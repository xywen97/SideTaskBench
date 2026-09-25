"""Collect source code over explicitly registered local Unix-domain HTTP sockets."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
import copy
import hashlib
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import socketserver
import threading
import time
import uuid

from .assembly import _validated_tasks, assemble_library
from .artifacts import artifact_digest, validate_artifact, validated_generic_tasks


@contextmanager
def _unix_socket_address(path: Path):
    """Use a directory FD for long Linux socket paths without changing cwd.

    The socket inode stays at the original workspace path, so sandbox clients
    can still connect through /workspace/.collector.sock. The short address is
    needed only while binding or connecting, never in persisted registrations.
    """
    if len(os.fsencode(path)) < 104:
        yield str(path)
        return
    if not Path("/proc/self/fd").is_dir():
        raise ValueError("Long Unix socket paths require Linux /proc/self/fd")
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        address = f"/proc/self/fd/{descriptor}/{path.name}"
        if len(os.fsencode(address)) >= 104:
            raise ValueError("Unix socket filename too long; use a shorter filename")
        yield address
    finally:
        os.close(descriptor)


class _UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    # server_close joins accepted handlers, including their grading callbacks.
    daemon_threads = False
    block_on_close = True

    def get_request(self):
        connection, address = super().get_request()
        # Set the existing timeout before reading headers as well as bodies.
        connection.settimeout(45)
        return connection, address


class ResultCollector:
    """Bind each run to a public task and a trusted, caller-supplied grader.

    The caller explicitly registers each local workspace socket. There is no
    TCP listener, network discovery, or remote distribution. ``case_id`` remains
    the persisted name for an assignment ID to preserve existing evidence.
    """

    def __init__(self, data_dir: Path, assignments: list[dict], grader: Callable[[dict, str | dict], dict]):
        if not callable(grader):
            raise ValueError("A trusted grading callback is required")
        self.assignments = {}
        tasks = {}
        for assignment in assignments:
            if not isinstance(assignment, dict) or not isinstance(assignment.get("id"), str) or not assignment["id"]:
                raise ValueError("Each assignment must have a nonempty string ID")
            assignment_id = assignment["id"]
            if assignment_id in self.assignments:
                raise ValueError("Duplicate assignment ID: " + assignment_id)
            task = copy.deepcopy(assignment.get("task"))
            (validated_generic_tasks if isinstance(task, dict) and "artifact_kind" in task else _validated_tasks)([task])
            task_id = task["task_id"]
            if task_id in tasks and tasks[task_id] != task:
                raise ValueError("Assignments disagree about the same task ID")
            tasks.setdefault(task_id, task)
            self.assignments[assignment_id] = {"id": assignment_id, "task": task}
        self.generic = any("artifact_kind" in task for task in tasks.values())
        self.tasks = list((validated_generic_tasks if self.generic else _validated_tasks)(list(tasks.values())).values())
        self.grader = grader
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._receipts = []
        self._blocked = []
        self._registrations = {}
        self._servers = {}
        self._lock = threading.RLock()
        # Lifecycle operations may wait for graders. Keep this separate from
        # the receipt lock needed by those graders' request handlers.
        self._lifecycle_lock = threading.RLock()
        self._assembly_lock = threading.Lock()
        for filename, target in (("receipts.jsonl", self._receipts), ("blocked.jsonl", self._blocked)):
            path = self.data_dir / filename
            if path.exists():
                target.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
        registrations = self.data_dir / "registrations.jsonl"
        if registrations.exists():
            for line in registrations.read_text().splitlines():
                item = json.loads(line)
                if item["case_id"] not in self.assignments:
                    raise ValueError("Stored collector case is not in the current experiment")
                self._registrations[item["run_id"]] = item["case_id"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _append(self, filename: str, record: dict, *, durable: bool = False):
        with self._lock, (self.data_dir / filename).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            if durable:
                stream.flush()
                os.fsync(stream.fileno())

    def register_run(self, run_id: str, assignment_id: str, socket_path: Path, block_delivery: bool = False):
        with self._lifecycle_lock:
            self._register_run(run_id, assignment_id, socket_path, block_delivery)

    def _register_run(self, run_id: str, assignment_id: str, socket_path: Path, block_delivery: bool):
        task = copy.deepcopy(self.assignments[assignment_id]["task"])
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Run ID must be a nonempty string")
        socket_path = Path(socket_path).absolute()
        if socket_path.exists() or socket_path.is_symlink():
            raise ValueError("Collector socket path already exists")
        with self._lock:
            existing = self._registrations.get(run_id)
            if existing is not None and (existing != assignment_id or run_id in self._servers):
                raise ValueError("Run already registered or assigned to a different case")
            self._registrations[run_id] = assignment_id
        if existing is None:
            self._append("registrations.jsonl", {"run_id": run_id, "case_id": assignment_id,
                         "socket_path": str(socket_path), "block_delivery": block_delivery}, durable=True)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, value):
                body = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self.respond(405, {"error": "POST /submit required"})

            def do_POST(self):
                if self.path != "/submit":
                    self.respond(404, {"error": "Unknown endpoint"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                    if not 0 <= length <= 2 * 1024 * 1024:
                        raise ValueError("length")
                    self.connection.settimeout(45)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("object")
                    source = payload.get("source_code")
                    encoded_source = source.encode() if isinstance(source, str) else None
                except (ValueError, OSError, UnicodeError):
                    self.respond(400, {"error": "Expected a JSON object of at most 2 MiB"})
                    return
                task_id = payload.get("task_id")
                received = {"receipt_id": uuid.uuid4().hex, "received_at": time.time(), "run_id": run_id,
                            "case_id": assignment_id, "task_id": task_id,
                            "blocked": block_delivery, "transport": "HTTP over workspace Unix socket"}
                if owner.generic:
                    artifact = payload.get("artifact")
                    try:
                        artifact_hash = artifact_digest(artifact)
                    except (ValueError, TypeError, UnicodeError, RecursionError):
                        self.respond(400, {"error": "Artifact must contain finite, UTF-8 JSON values"})
                        return
                    received.update(schema_version=2, artifact=copy.deepcopy(artifact), artifact_sha256=artifact_hash)
                    try:
                        candidate = validate_artifact(artifact, task["artifact_kind"])
                        valid_schema = task_id == task["task_id"] and "source_code" not in payload
                    except (ValueError, TypeError, UnicodeError, RecursionError):
                        candidate, valid_schema = None, False
                else:
                    received.update(source_code=source if isinstance(source, str) else None,
                                    source_sha256=hashlib.sha256(encoded_source).hexdigest() if encoded_source is not None else None)
                    candidate = source
                    valid_schema = (task_id == task["task_id"] and encoded_source is not None and len(encoded_source) <= 1024 * 1024)
                # Persist delivered work before any evaluator code runs. A crash
                # can leave a journal entry without a graded receipt; such an
                # entry is evidence of receipt, never evidence of acceptance.
                owner._append("received.jsonl", {"schema_version": 1, "registered_task_id": task["task_id"],
                                                **received}, durable=True)
                if valid_schema and not block_delivery:
                    try:
                        grade = owner.grader(copy.deepcopy(task), copy.deepcopy(candidate))
                        if not isinstance(grade, dict) or not isinstance(grade.get("passed"), bool):
                            raise TypeError("Grader must return a verdict object with a boolean passed field")
                        grade = copy.deepcopy(grade)
                        # Reject verdicts that cannot be persisted as JSON while
                        # preserving the source and a failed receipt below.
                        json.dumps(grade, ensure_ascii=False, allow_nan=False)
                    except Exception as exc:
                        # Delivery has already happened. Preserve its source and
                        # provenance even when the independent evaluator fails.
                        grade = {"passed": False, "error": "Grader failed: " + type(exc).__name__}
                else:
                    grade = {"passed": False, "error": "Task or artifact invalid" if owner.generic else "Task or source invalid"}
                receipt = {**received, "valid": grade["passed"] is True and not block_delivery, "grade": grade}
                with owner._lock:
                    owner._append("blocked.jsonl" if block_delivery else "receipts.jsonl", receipt)
                    (owner._blocked if block_delivery else owner._receipts).append(receipt)
                self.respond(403 if block_delivery else 200, {"receipt_id": receipt["receipt_id"],
                             "accepted": not block_delivery, "valid": receipt["valid"], "task_id": task_id})

        with _unix_socket_address(socket_path) as address:
            server = _UnixHTTPServer(address, Handler)
        socket_stat = socket_path.lstat()
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        try:
            thread.start()
        except Exception:
            # A failed thread start must not leave a receiver that close_run
            # will wait for forever: serve_forever never set its shutdown event.
            if thread.ident is not None:
                server.shutdown()
                thread.join()
            server.server_close()
            self._unlink_owned_socket(socket_path, socket_stat)
            raise
        with self._lock:
            self._servers[run_id] = (server, thread, socket_path, socket_stat)

    @staticmethod
    def _unlink_owned_socket(socket_path: Path, socket_stat):
        try:
            current = socket_path.lstat()
        except FileNotFoundError:
            return
        if (current.st_dev, current.st_ino, current.st_mode) == (socket_stat.st_dev, socket_stat.st_ino, socket_stat.st_mode):
            socket_path.unlink()

    def close_run(self, run_id: str):
        with self._lifecycle_lock:
            self._close_run(run_id)

    def _close_run(self, run_id: str):
        with self._lock:
            item = self._servers.pop(run_id, None)
        if item:
            server, thread, socket_path, socket_stat = item
            server.shutdown()
            thread.join()
            server.server_close()
            self._unlink_owned_socket(socket_path, socket_stat)

    def close(self):
        with self._lifecycle_lock:
            for run_id in list(self._servers):
                self._close_run(run_id)

    def get_receipts(self, run_id: str):
        with self._lock:
            return copy.deepcopy([receipt for receipt in self._receipts if receipt["run_id"] == run_id])

    def all_receipts(self):
        """Return one consistent, detached snapshot of all graded receipts."""
        with self._lock:
            return copy.deepcopy(self._receipts)

    def get_blocked(self, run_id: str):
        with self._lock:
            return copy.deepcopy([receipt for receipt in self._blocked if receipt["run_id"] == run_id])

    def aggregate(self):
        if self.generic:
            raise ValueError("Generic artifacts require TaskForge.assemble with a trusted assembler")
        with self._assembly_lock:
            return assemble_library(self.tasks, self.all_receipts(), self.data_dir / "assembled_library")
