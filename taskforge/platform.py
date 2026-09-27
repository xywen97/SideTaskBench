"""Local platform lifecycle: requirement, frozen plan, assignment and result."""

from contextlib import contextmanager
import copy
import errno
import hashlib
import json
from pathlib import Path
import socket
import stat
import threading

from .assembly import assemble_library
from .artifact_assembly import assemble_artifacts, output_inventory
from .artifacts import validate_artifact_receipt
from .collection import ResultCollector, _unix_socket_address
from .distribution import render_reference, write_reference
from .models import TaskPlan, digest, identifier
from .planning import Planner, SpecificationPlanner
from .storage import JobStore


class TaskForge:
    """A persisted job. Delivery is limited to explicitly registered local workspaces."""

    def __init__(self, directory: Path):
        self.store = JobStore(directory)
        self._lock = threading.RLock()
        self._collector = None
        metadata = self.store.read("job.json")
        raw = self.store.read("plan.json")
        if metadata.get("plan_sha256") != digest(raw) or metadata.get("request_sha256") != digest(self.store.read("request.json")):
            raise ValueError("Frozen request or plan has changed")
        self._plan = TaskPlan.from_dict(raw)
        self._tasks = {task["task_id"]: copy.deepcopy(task) for task in self._plan.tasks}
        self.collector_directory = JobStore(Path(metadata["collector_directory"])).root

    @classmethod
    def create(cls, directory: Path, request: dict, *, planner: Planner | None = None,
               collector_directory: Path | None = None) -> "TaskForge":
        plan = (planner or SpecificationPlanner()).plan(copy.deepcopy(request))
        # Validate custom planners through the same serializable contract.
        plan = TaskPlan.from_dict(plan.to_dict())
        store = JobStore(directory)
        if store.root.exists() and any(store.root.iterdir()):
            raise ValueError("Create a job in a new empty directory")
        collector = JobStore(collector_directory or store.root / "collector").root
        if store.root.is_relative_to(collector):
            raise ValueError("Collector storage must not contain the job directory")
        if collector.exists() and (not collector.is_dir() or any(collector.iterdir())):
            raise ValueError("A new job requires empty collector storage")
        store.write("request.json", request)
        store.write("plan.json", plan.to_dict())
        store.write("job.json", {"schema_version": 1, "job_id": plan.job_id, "plan_sha256": digest(plan.to_dict()),
                                 "request_sha256": digest(request), "collector_directory": str(collector)})
        return cls(store.root)

    @property
    def plan(self) -> dict:
        return self._plan.to_dict()

    @property
    def collector(self) -> ResultCollector:
        if self._collector is None:
            raise RuntimeError("Open a delivery session first")
        return self._collector

    @contextmanager
    def _access(self):
        """Serialize mutations/snapshots, sharing this instance's session lease."""
        with self._lock:
            if self._collector is not None:
                yield
            else:
                with self.store.session_lock():
                    yield

    def _checked_workspace(self, workspace: Path) -> Path:
        original = Path(workspace).absolute()
        if original.is_symlink() or any(parent.is_symlink() for parent in original.parents):
            raise ValueError("Registered workspace must not traverse symlinks")
        target = original.resolve(strict=True)
        if not target.is_dir() or any(target.is_relative_to(root) or root.is_relative_to(target)
                                      for root in (self.store.root, self.collector_directory)):
            raise ValueError("Workspace must be a directory that cannot expose platform state")
        return target

    def _recover_socket(self, item: dict, path: Path) -> None:
        """Remove only a dead Unix socket with a matching persisted registration."""
        try:
            before = path.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISSOCK(before.st_mode):
            raise ValueError("Collector socket path already exists and is not a socket")
        journal = JobStore(self.collector_directory).path("registrations.jsonl")
        registrations = [json.loads(line) for line in journal.read_text().split("\n") if line.strip()] if journal.exists() else []
        if not any(record.get("run_id") == item["assignment_id"] and record.get("case_id") == item["routing_id"]
                   and record.get("socket_path") == str(path) for record in registrations):
            raise ValueError("Collector socket has no matching persisted registration")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            try:
                with _unix_socket_address(path) as address:
                    probe.connect(address)
            except OSError as exc:
                if exc.errno not in {errno.ECONNREFUSED, errno.ENOENT}:
                    raise ValueError("Collector socket liveness could not be established") from exc
            else:
                raise ValueError("Collector socket still has a live receiver")
        try:
            after = path.lstat()
        except FileNotFoundError:
            return
        if (after.st_dev, after.st_ino, after.st_mode) != (before.st_dev, before.st_ino, before.st_mode):
            raise ValueError("Collector socket changed during recovery")
        path.unlink()

    def assign(self, task_id: str, assignment_id: str, workspace: Path, reference: dict, *,
               condition: str = "wrapped", variant: str = "compatibility_v3", routing_id: str | None = None,
               reference_text: str | None = None) -> dict:
        """Deliver a rendered or caller-frozen reference into a registered repository."""
        identifier(assignment_id)
        task = self._tasks[task_id]
        workspace = self._checked_workspace(workspace)
        text = render_reference(reference, task, condition, variant)
        if reference_text is not None:
            if not isinstance(reference_text, str) or not reference_text.strip():
                raise ValueError("Frozen reference must be nonempty text")
            text = reference_text
        value = {"assignment_id": assignment_id, "task_id": task_id, "routing_id": identifier(routing_id or task_id),
                 "workspace": str(workspace), "condition": condition, "variant": variant,
                 "plan_sha256": digest(self.plan), "reference": copy.deepcopy(reference),
                 "reference_sha256": hashlib.sha256(text.encode()).hexdigest(), "state": "prepared"}
        with self._access():
            path = self.store.path("assignments/" + assignment_id + ".json")
            if path.exists():
                previous = self.store.assignment(assignment_id)
                if {k: v for k, v in previous.items() if k != "state"} != {k: v for k, v in value.items() if k != "state"}:
                    raise ValueError("An assignment ID cannot be rebound to another task, workspace or document")
                if previous["state"] not in {"prepared", "interrupted"}:
                    raise ValueError("Use a new assignment ID for another attempt")
            write_reference(workspace, text)
            self.store.save_assignment(value)
        return copy.deepcopy(value)

    @contextmanager
    def session(self, grader, *, evaluator_id: str, bindings: dict[str, str] | None = None):
        """Own local HTTP receivers for this job; no Agent or LLM is invoked here."""
        if self._collector is not None:
            raise RuntimeError("Session already active")
        if not isinstance(evaluator_id, str) or not evaluator_id:
            raise ValueError("An evaluator version/identity is required")
        routes = dict(bindings or {task_id: task_id for task_id in self._tasks})
        for route, task_id in routes.items():
            identifier(route)
            if task_id not in self._tasks:
                raise ValueError("Unknown task in delivery bindings")
        config = {"evaluator_id": evaluator_id, "bindings": routes, "plan_sha256": digest(self.plan)}
        with self.store.session_lock():
            if self.store.path("delivery.json").exists() and self.store.read("delivery.json") != config:
                raise ValueError("Evaluator identity and task bindings are frozen for this job")
            self.store.write("delivery.json", config)
            for item in self.store.assignments():
                if item["state"] == "active":
                    item["state"] = "interrupted"
                    self.store.save_assignment(item)
            self._collector = ResultCollector(self.collector_directory,
                [{"id": route, "task": self._tasks[task_id]} for route, task_id in routes.items()], grader)
            try:
                yield self
            finally:
                with self._lock:
                    try:
                        self._collector.close()
                    finally:
                        self._collector = None
                        for item in self.store.assignments():
                            if item["state"] == "active":
                                item["state"] = "interrupted"
                                self.store.save_assignment(item)

    def open_delivery(self, assignment_id: str) -> None:
        with self._lock:
            item = self.store.assignment(assignment_id)
            if item["state"] not in {"prepared", "interrupted"}:
                raise ValueError("Assignment is not ready for delivery")
            target = self.collector.assignments.get(item["routing_id"], {}).get("task", {})
            if target.get("task_id") != item["task_id"] or item["plan_sha256"] != digest(self.plan):
                raise ValueError("Assignment does not match the frozen delivery plan")
            workspace = self._checked_workspace(Path(item["workspace"]))
            reference = JobStore(workspace).path("docs/reference.md")
            if not reference.is_file() or not stat.S_ISREG(reference.stat().st_mode):
                raise ValueError("Registered reference must remain a regular file")
            if hashlib.sha256(reference.read_bytes()).hexdigest() != item["reference_sha256"]:
                raise ValueError("Registered reference has changed since assignment")
            self._recover_socket(item, workspace / ".collector.sock")
            # Record intent before creating the receiver so a process death at
            # either point leaves an assignment that the next session can retry.
            item["state"] = "active"
            self.store.save_assignment(item)
            try:
                self.collector.register_run(assignment_id, item["routing_id"], workspace / ".collector.sock")
            except BaseException:
                item["state"] = "interrupted"
                self.store.save_assignment(item)
                raise

    def close_delivery(self, assignment_id: str, *, interrupted: bool = False) -> None:
        with self._lock:
            self.collector.close_run(assignment_id)
            item = self.store.assignment(assignment_id)
            item["state"] = "interrupted" if interrupted else "closed"
            self.store.save_assignment(item)

    def _receipts(self) -> list[dict]:
        path = JobStore(self.collector_directory).path("receipts.jsonl")
        if self._collector is not None:
            receipts = self._collector.all_receipts()
        else:
            receipts = [json.loads(line) for line in path.read_text().split("\n") if line.strip()] if path.exists() else []
        assignments = {item["assignment_id"]: item for item in self.store.assignments()}
        for receipt in receipts:
            assignment = assignments.get(receipt.get("run_id"))
            if assignment is None or receipt.get("case_id") != assignment["routing_id"]:
                raise ValueError("Receipt has no matching platform assignment")
            if self._plan.schema_version == 2:
                validate_artifact_receipt(receipt, self._tasks[assignment["task_id"]])
                continue
            if receipt.get("valid"):
                if receipt.get("task_id") != assignment["task_id"] or receipt.get("grade", {}).get("passed") is not True or receipt.get("blocked"):
                    raise ValueError("Accepted receipt does not match its registered task and grade")
                source = receipt.get("source_code")
                if not isinstance(source, str) or receipt.get("source_sha256") != hashlib.sha256(source.encode()).hexdigest():
                    raise ValueError("Receipt source hash mismatch")
        return receipts

    def status(self) -> dict:
        with self._access():
            receipts = self._receipts()
            accepted = {item["task_id"] for item in receipts if item.get("valid") is True}
            result = {"job_id": self._plan.job_id, "objective": self._plan.objective,
                    "state": "complete" if len(accepted) == len(self._tasks) else "pending",
                    "completed_tasks": len(accepted), "total_tasks": len(self._tasks),
                    "tasks": [{"task_id": task_id, "state": "fulfilled" if task_id in accepted else "pending"} for task_id in self._tasks],
                    "assignments": self.store.assignments(), "submission_count": len(receipts)}
            if self._plan.schema_version == 2:
                aggregate = self._fresh_aggregate(receipts)
                complete = aggregate is not None and aggregate["final_grade"]["passed"]
                result.update(state="complete" if complete else "pending", large_task_complete=complete,
                              aggregate_fresh=aggregate is not None,
                              final_grade=copy.deepcopy(aggregate["final_grade"]) if aggregate else None)
                for item in result["tasks"]:
                    item["optional"] = self._tasks[item["task_id"]].get("optional", False)
            return result

    def _fresh_aggregate(self, receipts: list[dict]) -> dict | None:
        path = self.store.path("result.json")
        if not path.exists():
            return None
        try:
            result = self.store.read("result.json")
        except (OSError, ValueError):
            return None
        if (not isinstance(result, dict) or result.get("schema_version") != 2 or result.get("plan_sha256") != digest(self.plan)
                or result.get("assembly_receipts_sha256") != digest(receipts)
                or not isinstance(result.get("final_grade"), dict)
                or type(result["final_grade"].get("passed")) is not bool
                or result.get("large_task_complete") is not result["final_grade"]["passed"]):
            return None
        try:
            inventory = output_inventory(self.store.path("result/artifacts"))
        except (ValueError, OSError):
            return None
        return result if inventory == result.get("output_sha256") else None

    def assemble(self, *, assembler=None) -> dict:
        """Publish only received, accepted modules; report missing tasks explicitly."""
        with self._access():
            receipts = self._receipts()
            if self._plan.schema_version == 2:
                result = assemble_artifacts(self.plan, receipts, self.store.path("result/artifacts"), assembler)
                result["assembly_receipts_sha256"] = digest(receipts)
            else:
                result = assemble_library(list(self._tasks.values()), receipts, self.store.path("result/package"))
            result.update(job_id=self._plan.job_id, objective=self._plan.objective, plan_sha256=digest(self.plan))
            self.store.write("result.json", result)
            return result
