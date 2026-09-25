"""Persisted TaskForge jobs exercised through their public local-delivery API."""

import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock

from taskforge import TaskForge


TASKS = [
    {"task_id": "unit-double", "function_name": "double", "signature": "double(value)",
     "language": "python", "description": "Return twice the numeric input.",
     "requirements": "Accept an integer and return twice its value without side effects.",
     "examples": [{"input": 3, "output": 6}]},
    {"task_id": "unit-square", "function_name": "square", "signature": "square(value)",
     "language": "python", "description": "Return the square of the numeric input.",
     "requirements": "Accept an integer and return its square without side effects.",
     "examples": [{"input": 3, "output": 9}]},
]
SOURCES = {
    "unit-double": "def double(value):\n    return value * 2\n",
    "unit-square": "def square(value):\n    return value * value\n",
}
ALTERNATE_DOUBLE = "def double(value):\n    return value + value\n"
REFERENCE = {
    "topic": "Integer arithmetic",
    "text": "Python integer arithmetic has arbitrary precision.",
    "compatibility_context": "The application uses integer arithmetic in its public API.",
}


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class TaskForgePlatformTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tfp-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = {"job_id": "arithmetic-library", "objective": "Build two integer arithmetic helpers.",
                        "components": copy.deepcopy(TASKS)}
        self.grader = Mock(side_effect=lambda task, source: {
            "passed": source == SOURCES[task["task_id"]] or (
                task["task_id"] == "unit-double" and source == ALTERNATE_DOUBLE),
            "tests_run": 1,
        })

    def create(self, name="job"):
        return TaskForge.create(self.root / name, self.request)

    def assign(self, job, assignment_id="attempt-double", task_id="unit-double", **kwargs):
        workspace = self.root / ("w-" + assignment_id)
        workspace.mkdir(exist_ok=True)
        assignment = job.assign(task_id, assignment_id, workspace, REFERENCE, **kwargs)
        return workspace, assignment

    def submit(self, workspace, task_id, source, **extra):
        connection = UnixConnection(workspace / ".collector.sock")
        try:
            payload = {"task_id": task_id, "source_code": source, **extra}
            connection.request("POST", "/submit", json.dumps(payload).encode(),
                               {"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            return json.loads(response.read())
        finally:
            connection.close()

    def test_full_lifecycle_collects_two_tasks_and_assembles_only_received_sources(self):
        job = self.create()
        routes = {"repair-a": "unit-double", "repair-b": "unit-square"}
        workspaces = {}
        for index, task in enumerate(TASKS):
            route = list(routes)[index]
            workspace, assignment = self.assign(job, "attempt-" + str(index), task["task_id"], routing_id=route)
            workspaces[task["task_id"]] = workspace
            self.assertEqual(assignment["state"], "prepared")
            reference = (workspace / "docs/reference.md").read_text()
            self.assertIn(task["signature"], reference)
            self.assertIn(task["requirements"], reference)
            self.assertIn("/workspace/.collector.sock", reference)
        self.assertEqual(job.status()["state"], "pending")
        with job.session(self.grader, evaluator_id="arithmetic-v1", bindings=routes) as session:
            self.assertIs(session, job)
            for index, task in enumerate(TASKS):
                assignment_id = "attempt-" + str(index)
                job.open_delivery(assignment_id)
                response = self.submit(workspaces[task["task_id"]], task["task_id"], SOURCES[task["task_id"]],
                                       run_id="untrusted-run", case_id="untrusted-route")
                self.assertTrue(response["accepted"])
                self.assertTrue(response["valid"])
                job.close_delivery(assignment_id)
                self.assertFalse((workspaces[task["task_id"]] / ".collector.sock").exists())
                receipt = job.collector.get_receipts(assignment_id)[0]
                self.assertEqual(receipt["run_id"], assignment_id)
                self.assertEqual(receipt["case_id"], list(routes)[index])
                self.assertEqual(receipt["receipt_id"], response["receipt_id"])
        status = job.status()
        self.assertEqual((status["state"], status["completed_tasks"], status["submission_count"]), ("complete", 2, 2))
        self.assertTrue(all(item["state"] == "fulfilled" for item in status["tasks"]))
        self.assertTrue(all(item["state"] == "closed" for item in status["assignments"]))
        result = job.assemble()
        self.assertTrue(result["large_task_complete"])
        self.assertEqual(result["job_id"], self.request["job_id"])
        self.assertEqual(result["effective_work_units"], 2)
        self.assertEqual(json.loads((self.root / "job/result.json").read_text()), result)
        package = Path(result["library_path"])
        self.assertEqual({path.name for path in package.iterdir()}, {"__init__.py", "double.py", "square.py"})
        for task in TASKS:
            self.assertEqual((package / (task["function_name"] + ".py")).read_text(), SOURCES[task["task_id"]])
        self.assertEqual((package / "__init__.py").read_text(), "from .double import double\nfrom .square import square\n")
        self.assertEqual(self.grader.call_count, 2)
        with self.assertRaisesRegex(RuntimeError, "session"):
            _ = job.collector

    def test_partial_results_keep_failed_receipts_and_deduplicate_by_first_valid_task(self):
        job = self.create()
        workspace, _ = self.assign(job)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            failed = self.submit(workspace, "unit-double", "def double(value):\n    return 0\n")
            first = self.submit(workspace, "unit-double", SOURCES["unit-double"])
            second = self.submit(workspace, "unit-double", ALTERNATE_DOUBLE)
            job.close_delivery("attempt-double")
        self.assertFalse(failed["valid"])
        self.assertTrue(first["valid"])
        self.assertTrue(second["valid"])
        self.assertNotEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(job.status()["completed_tasks"], 1)
        self.assertEqual(job.status()["state"], "pending")
        result = job.assemble()
        self.assertEqual((result["submission_count"], result["valid_submissions"], result["completed_tasks"]), (3, 2, 1))
        self.assertFalse(result["large_task_complete"])
        completed, missing = result["task_results"]
        self.assertEqual(completed["receipt_id"], first["receipt_id"])
        self.assertEqual(completed["source_code"], SOURCES["unit-double"])
        self.assertEqual(completed["source_sha256"], hashlib.sha256(SOURCES["unit-double"].encode()).hexdigest())
        self.assertFalse(missing["complete"])
        self.assertNotIn("source_code", missing)
        self.assertFalse((Path(result["library_path"]) / "square.py").exists())

    def test_wrong_task_payload_cannot_select_another_grader_or_fulfill_another_task(self):
        job = self.create()
        workspace, _ = self.assign(job)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            response = self.submit(workspace, "unit-square", SOURCES["unit-square"])
            job.close_delivery("attempt-double")
        self.assertFalse(response["valid"])
        self.grader.assert_not_called()
        self.assertEqual(job.status()["submission_count"], 1)
        self.assertEqual(job.assemble()["completed_tasks"], 0)

    def test_restart_retains_status_and_resumes_interrupted_assignment(self):
        job = self.create()
        workspace, _ = self.assign(job)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            first = self.submit(workspace, "unit-double", SOURCES["unit-double"])
            self.assertEqual(job.status()["assignments"][0]["state"], "active")
            # Session cleanup must retain recoverable work if close_delivery was omitted.
        self.assertFalse((workspace / ".collector.sock").exists())
        restarted = TaskForge(self.root / "job")
        self.assertEqual(restarted.status(), job.status())
        self.assertEqual(restarted.status()["assignments"][0]["state"], "interrupted")
        with restarted.session(self.grader, evaluator_id="arithmetic-v1"):
            restarted.open_delivery("attempt-double")
            second = self.submit(workspace, "unit-double", ALTERNATE_DOUBLE)
            restarted.close_delivery("attempt-double")
        self.assertTrue(second["valid"])
        result = restarted.assemble()
        self.assertEqual(result["submission_count"], 2)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(result["task_results"][0]["receipt_id"], first["receipt_id"])
        registrations = (self.root / "job/collector/registrations.jsonl").read_text().splitlines()
        self.assertEqual(len(registrations), 1)

    def test_assignment_identity_cannot_be_rebound_and_closed_attempt_cannot_be_reused(self):
        job = self.create()
        workspace, assignment = self.assign(job)
        self.assertEqual(job.assign("unit-double", "attempt-double", workspace, REFERENCE), assignment)
        another_workspace = self.root / "another-workspace"
        another_workspace.mkdir()
        changes = [
            ("unit-square", workspace, REFERENCE, {}),
            ("unit-double", another_workspace, REFERENCE, {}),
            ("unit-double", workspace, {**REFERENCE, "text": "Changed reference facts."}, {}),
            ("unit-double", workspace, REFERENCE, {"routing_id": "another-route"}),
        ]
        for task_id, target, reference, kwargs in changes:
            with self.subTest(task_id=task_id, target=target, kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "rebound"):
                    job.assign(task_id, "attempt-double", target, reference, **kwargs)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            job.close_delivery("attempt-double")
            with self.assertRaisesRegex(ValueError, "not ready"):
                job.open_delivery("attempt-double")
        with self.assertRaisesRegex(ValueError, "new assignment ID"):
            job.assign("unit-double", "attempt-double", workspace, REFERENCE)

    def test_evaluator_identity_and_delivery_bindings_remain_frozen_across_restart(self):
        job = self.create()
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            pass
        restarted = TaskForge(self.root / "job")
        changes = [
            {"evaluator_id": "arithmetic-v2"},
            {"evaluator_id": "arithmetic-v1", "bindings": {"unit-double": "unit-square", "unit-square": "unit-double"}},
            {"evaluator_id": "arithmetic-v1", "bindings": {"different-route": "unit-double"}},
        ]
        before = (self.root / "job/delivery.json").read_bytes()
        for kwargs in changes:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "frozen"):
                with restarted.session(self.grader, **kwargs):
                    self.fail("Changed evaluator or route mapping acquired a delivery session")
        self.assertEqual((self.root / "job/delivery.json").read_bytes(), before)
        with restarted.session(self.grader, evaluator_id="arithmetic-v1"):
            pass

    def test_invalid_session_configuration_and_delivery_without_session_are_rejected(self):
        job = self.create()
        self.assign(job)
        with self.assertRaisesRegex(RuntimeError, "session"):
            job.open_delivery("attempt-double")
        with self.assertRaisesRegex(ValueError, "identity"):
            with job.session(self.grader, evaluator_id=""):
                self.fail("Missing evaluator identity was accepted")
        with self.assertRaisesRegex(ValueError, "Unknown task"):
            with job.session(self.grader, evaluator_id="arithmetic-v1", bindings={"route": "missing-task"}):
                self.fail("Unknown delivery task was accepted")

    def test_session_ownership_is_exclusive_across_instances_and_released_on_failure(self):
        first = self.create()
        second = TaskForge(self.root / "job")
        with self.assertRaisesRegex(RuntimeError, "synthetic caller failure"):
            with first.session(self.grader, evaluator_id="arithmetic-v1"):
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    with first.session(self.grader, evaluator_id="arithmetic-v1"):
                        self.fail("Nested session acquired ownership")
                with self.assertRaisesRegex(RuntimeError, "active local delivery session"):
                    with second.session(self.grader, evaluator_id="arithmetic-v1"):
                        self.fail("Second instance acquired session ownership")
                raise RuntimeError("synthetic caller failure")
        with second.session(self.grader, evaluator_id="arithmetic-v1"):
            self.assertIsNotNone(second.collector)

    def test_request_and_plan_tampering_are_rejected_when_reopening_a_job(self):
        for filename in ("request.json", "plan.json"):
            with self.subTest(filename=filename):
                job = self.create(filename.split(".")[0])
                path = job.store.root / filename
                document = json.loads(path.read_text())
                document["objective"] = "A different unreviewed task"
                path.write_text(json.dumps(document))
                with self.assertRaisesRegex(ValueError, "Frozen request or plan"):
                    TaskForge(job.store.root)

    def test_assignment_plan_tampering_is_rejected_before_socket_registration(self):
        job = self.create()
        workspace, assignment = self.assign(job)
        assignment["plan_sha256"] = "0" * 64
        job.store.save_assignment(assignment)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            with self.assertRaisesRegex(ValueError, "frozen delivery plan"):
                job.open_delivery("attempt-double")
        self.assertFalse((workspace / ".collector.sock").exists())
        self.grader.assert_not_called()

    def test_plan_is_detached_from_caller_and_returned_mutations(self):
        job = self.create()
        expected = job.plan
        self.request["components"][0]["description"] = "Changed caller input"
        exposed = job.plan
        exposed["tasks"][0]["task_id"] = "changed-public-copy"
        exposed["analysis"]["unit_count"] = 999
        self.assertEqual(job.plan, expected)
        self.assertEqual(TaskForge(self.root / "job").plan, expected)

    def test_invalid_job_task_assignment_and_route_ids_cannot_create_paths(self):
        invalid_ids = ("", "../escape", "/absolute", "a/b", "bad\x00id", ".", "..", "x" * 129)
        for index, value in enumerate(invalid_ids):
            for field in ("job_id", "task_id"):
                request = copy.deepcopy(self.request)
                if field == "job_id":
                    request[field] = value
                else:
                    request["components"][0][field] = value
                target = self.root / ("invalid-" + field + str(index))
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    TaskForge.create(target, request)
                self.assertFalse(target.exists())
        job = self.create()
        workspace = self.root / "workspace"
        workspace.mkdir()
        for value in invalid_ids:
            with self.subTest(assignment_id=value), self.assertRaises(ValueError):
                job.assign("unit-double", value, workspace, REFERENCE)
            with self.subTest(routing_id=value):
                # None/empty currently means the default route; nonempty unsafe IDs must fail.
                if value:
                    with self.assertRaises(ValueError):
                        job.assign("unit-double", "valid-assignment", workspace, REFERENCE, routing_id=value)
        self.assertFalse((workspace / "docs/reference.md").exists())

    def test_job_and_collector_storage_refuse_symlink_roots_and_ancestors(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "link"
        link.symlink_to(real, target_is_directory=True)
        for target in (link, link / "nested"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "symlink"):
                TaskForge.create(target, self.request)
        with self.assertRaisesRegex(ValueError, "symlink"):
            TaskForge.create(self.root / "job", self.request, collector_directory=link / "collector")
        self.assertEqual(list(real.iterdir()), [])
        self.assertFalse((self.root / "job").exists())

    def test_create_refuses_nonempty_or_non_directory_collector_storage_before_writing_job(self):
        for kind in ("directory", "file"):
            with self.subTest(kind=kind):
                collector = self.root / ("collector-" + kind)
                if kind == "directory":
                    collector.mkdir()
                    existing = collector / "receipts.jsonl"
                else:
                    existing = collector
                existing.write_text("evidence belonging to another job\n")
                directory = self.root / ("job-" + kind)
                with self.assertRaisesRegex(ValueError, "empty collector storage"):
                    TaskForge.create(directory, self.request, collector_directory=collector)
                self.assertFalse(directory.exists())
                self.assertEqual(existing.read_text(), "evidence belonging to another job\n")

    def test_create_refuses_collector_equal_to_or_containing_job_before_writing_request(self):
        targets = [(self.root / "same", self.root / "same"),
                   (self.root / "ancestor/job", self.root / "ancestor")]
        for directory, collector in targets:
            with self.subTest(directory=directory, collector=collector):
                with self.assertRaisesRegex(ValueError, "contain the job directory"):
                    TaskForge.create(directory, self.request, collector_directory=collector)
                self.assertFalse(directory.exists())
                self.assertFalse(collector.exists())
        default = self.create("default-job")
        self.assertEqual(default.collector_directory, self.root / "default-job/collector")

    def test_symlinked_job_files_and_assembly_directory_are_rejected(self):
        job = self.create()
        outside = self.root / "outside-plan.json"
        plan = self.root / "job/plan.json"
        outside.write_bytes(plan.read_bytes())
        plan.unlink()
        plan.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            TaskForge(self.root / "job")
        result_target = self.root / "outside-result"
        result_target.mkdir()
        (self.root / "job/result").symlink_to(result_target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            job.assemble()
        self.assertEqual(list(result_target.iterdir()), [])

    def test_assignment_refuses_workspaces_exposing_platform_state(self):
        job = self.create()
        for target in (self.root, self.root / "job"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "platform state"):
                job.assign("unit-double", "unsafe-attempt", target, REFERENCE)
        self.assertFalse((self.root / "docs").exists())
        self.assertFalse((self.root / "job/docs").exists())

    def test_reference_delivery_refuses_directory_and_file_symlinks(self):
        job = self.create()
        outside = self.root / "outside"
        outside.mkdir()
        target = outside / "reference.md"
        target.write_text("unchanged outside reference")
        for kind in ("directory", "file"):
            workspace = self.root / ("workspace-" + kind)
            workspace.mkdir()
            if kind == "directory":
                (workspace / "docs").symlink_to(outside, target_is_directory=True)
            else:
                (workspace / "docs").mkdir()
                (workspace / "docs/reference.md").symlink_to(target)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "registered workspace"):
                job.assign("unit-double", "attempt-" + kind, workspace, REFERENCE)
        self.assertEqual(target.read_text(), "unchanged outside reference")
        self.assertEqual(job.status()["assignments"], [])

    def test_workspace_must_also_stay_outside_job_and_collector_directories(self):
        collector = self.root / "external-collector"
        job = TaskForge.create(self.root / "job", self.request, collector_directory=collector)
        for target in (self.root / "job/nested-workspace", collector, collector / "nested-workspace"):
            target.mkdir(parents=True, exist_ok=True)
            with self.subTest(target=target), self.assertRaises(ValueError):
                job.assign("unit-double", "unsafe-attempt", target, REFERENCE)
            self.assertFalse((target / "docs").exists())

    def test_open_delivery_revalidates_workspace_and_ancestor_symlinks(self):
        for kind in ("workspace", "ancestor"):
            with self.subTest(kind=kind):
                job = self.create("job-" + kind)
                group = self.root / ("group-" + kind)
                workspace = group / "workspace"
                workspace.mkdir(parents=True)
                job.assign("unit-double", "attempt-double", workspace, REFERENCE)
                outside = self.root / ("unregistered-" + kind)
                outside.mkdir()
                if kind == "workspace":
                    workspace.rename(group / "original-workspace")
                    workspace.symlink_to(outside, target_is_directory=True)
                    unexpected = outside / ".collector.sock"
                else:
                    group.rename(self.root / "original-group")
                    (outside / "workspace").mkdir()
                    group.symlink_to(outside, target_is_directory=True)
                    unexpected = outside / "workspace/.collector.sock"
                with self.assertRaises(ValueError):
                    with job.session(self.grader, evaluator_id="arithmetic-v1"):
                        job.open_delivery("attempt-double")
                self.assertFalse(unexpected.exists())

    def test_open_delivery_rejects_changed_or_symlinked_reference_without_writing_outside(self):
        for kind in ("content", "file-symlink", "directory-symlink"):
            with self.subTest(kind=kind):
                job = self.create("job-" + kind)
                workspace, _ = self.assign(job, "attempt-" + kind)
                reference = workspace / "docs/reference.md"
                outside = self.root / ("outside-" + kind)
                outside.mkdir()
                external_reference = outside / "reference.md"
                original = reference.read_bytes()
                # A same-content symlink must still fail the provenance check.
                external_reference.write_bytes(original)
                if kind == "content":
                    reference.write_bytes(original + b"\nAn unregistered change.\n")
                elif kind == "file-symlink":
                    reference.unlink()
                    reference.symlink_to(external_reference)
                else:
                    (workspace / "docs").rename(workspace / "original-docs")
                    (workspace / "docs").symlink_to(outside, target_is_directory=True)
                before = reference.read_bytes()
                with job.session(self.grader, evaluator_id="arithmetic-v1"):
                    with self.assertRaises(ValueError):
                        job.open_delivery("attempt-" + kind)
                self.assertFalse((workspace / ".collector.sock").exists())
                self.assertEqual(reference.read_bytes(), before)
                self.assertEqual(external_reference.read_bytes(), original)
                self.assertEqual({item.name for item in outside.iterdir()}, {"reference.md"})
                self.assertEqual(job.status()["assignments"][0]["state"], "prepared")
        self.grader.assert_not_called()

    def test_same_session_snapshots_do_not_accept_a_submission_until_grading_finishes(self):
        job = self.create()
        workspace, _ = self.assign(job)
        started, release = threading.Event(), threading.Event()

        def grader(task, source):
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("test grader was not released")
            return {"passed": True}

        with job.session(grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            with ThreadPoolExecutor(max_workers=1) as pool:
                request = pool.submit(self.submit, workspace, "unit-double", SOURCES["unit-double"])
                try:
                    self.assertTrue(started.wait(timeout=2))
                    during = job.status()
                    self.assertEqual((during["submission_count"], during["completed_tasks"]), (0, 0))
                    self.assertEqual(during["assignments"][0]["state"], "active")
                    partial = job.assemble()
                    self.assertEqual((partial["submission_count"], partial["completed_tasks"]), (0, 0))
                    self.assertFalse((Path(partial["library_path"]) / "double.py").exists())
                finally:
                    release.set()
                response = request.result(timeout=3)
            self.assertTrue(response["valid"])
            after = job.status()
            self.assertEqual((after["submission_count"], after["completed_tasks"]), (1, 1))
            accepted = job.assemble()
            self.assertEqual(accepted["task_results"][0]["receipt_id"], response["receipt_id"])
            self.assertEqual((Path(accepted["library_path"]) / "double.py").read_text(), SOURCES["unit-double"])
            # Earlier snapshots are detached and retain their original meaning.
            self.assertEqual(during["completed_tasks"], 0)
            self.assertEqual(partial["completed_tasks"], 0)
            job.close_delivery("attempt-double")

    def test_real_process_death_leaves_a_stale_registered_socket_that_can_resume(self):
        job = self.create()
        workspace, _ = self.assign(job)
        child_code = """
from pathlib import Path
import sys, threading
from taskforge import TaskForge
job = TaskForge(Path(sys.argv[1]))
with job.session(lambda task, source: {'passed': True}, evaluator_id='arithmetic-v1'):
    job.open_delivery('attempt-double')
    print('READY', flush=True)
    threading.Event().wait()
"""
        child = subprocess.Popen([sys.executable, "-u", "-c", child_code, str(self.root / "job")],
                                 cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)

        def cleanup():
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

        self.addCleanup(cleanup)
        self.assertTrue(select.select([child.stdout], [], [], 5)[0], "Platform child did not start")
        self.assertEqual(child.stdout.readline().strip(), "READY")
        first = self.submit(workspace, "unit-double", SOURCES["unit-double"])
        self.assertTrue(first["valid"])
        child.kill()
        child.wait(timeout=5)
        self.assertTrue((workspace / ".collector.sock").is_socket())
        restarted = TaskForge(self.root / "job")
        self.assertEqual(restarted.status()["assignments"][0]["state"], "active")
        with restarted.session(self.grader, evaluator_id="arithmetic-v1"):
            restarted.open_delivery("attempt-double")
            second = self.submit(workspace, "unit-double", ALTERNATE_DOUBLE)
            restarted.close_delivery("attempt-double")
        self.assertTrue(second["valid"])
        self.assertFalse((workspace / ".collector.sock").exists())
        result = restarted.assemble()
        self.assertEqual(result["submission_count"], 2)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(result["task_results"][0]["receipt_id"], first["receipt_id"])
        self.assertEqual(result["task_results"][0]["source_code"], SOURCES["unit-double"])

    def test_unregistered_stale_socket_is_not_deleted_during_recovery(self):
        job = self.create()
        workspace, _ = self.assign(job)
        path = workspace / ".collector.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as unrelated:
            unrelated.bind(str(path))
        self.assertTrue(path.is_socket())
        with self.assertRaises(ValueError):
            with job.session(self.grader, evaluator_id="arithmetic-v1"):
                job.open_delivery("attempt-double")
        self.assertTrue(path.is_socket())

    def test_registered_path_that_is_now_a_file_or_symlink_is_not_deleted(self):
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind):
                job = self.create("job-" + kind)
                workspace, _ = self.assign(job, "attempt-" + kind)
                with job.session(self.grader, evaluator_id="arithmetic-v1"):
                    job.open_delivery("attempt-" + kind)
                path = workspace / ".collector.sock"
                outside = self.root / ("outside-" + kind)
                outside.write_text("unrelated content")
                if kind == "file":
                    path.write_text("unrelated content")
                else:
                    path.symlink_to(outside)
                restarted = TaskForge(job.store.root)
                with self.assertRaises(ValueError):
                    with restarted.session(self.grader, evaluator_id="arithmetic-v1"):
                        restarted.open_delivery("attempt-" + kind)
                self.assertEqual(path.read_text(), "unrelated content")
                self.assertEqual(outside.read_text(), "unrelated content")
                if kind == "symlink":
                    self.assertTrue(path.is_symlink())

    def test_registered_but_live_socket_is_not_deleted_during_recovery(self):
        job = self.create()
        workspace, _ = self.assign(job)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
        path = workspace / ".collector.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as live:
            live.bind(str(path))
            live.listen()
            with self.assertRaises(ValueError):
                with job.session(self.grader, evaluator_id="arithmetic-v1"):
                    job.open_delivery("attempt-double")
            self.assertTrue(path.is_socket())

    def test_long_path_recovery_preserves_live_socket_and_replaces_dead_socket(self):
        self.root = self.root / ("长目录" * 25)
        self.root.mkdir()
        job = self.create()
        workspace, _ = self.assign(job)
        path = workspace / ".collector.sock"
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
        self.assertFalse(path.exists())
        # Bind via a child cwd independently of the collector's path handling.
        child = subprocess.Popen([sys.executable, "-u", "-c", """
import socket, threading
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as receiver:
    receiver.bind('.collector.sock')
    receiver.listen()
    print('READY', flush=True)
    threading.Event().wait()
"""], cwd=workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready, _, _ = select.select([child.stdout], [], [], 5)
            self.assertTrue(ready, "Receiver did not start")
            self.assertEqual(child.stdout.readline().strip(), "READY")
            with job.session(self.grader, evaluator_id="arithmetic-v1"):
                with self.assertRaisesRegex(ValueError, "live receiver"):
                    job.open_delivery("attempt-double")
            self.assertTrue(path.is_socket())
        finally:
            child.kill()
            child.communicate(timeout=5)
        with job.session(self.grader, evaluator_id="arithmetic-v1"):
            job.open_delivery("attempt-double")
            self.assertTrue(path.is_socket())
            self.assertEqual(job.status()["assignments"][0]["state"], "active")
        self.assertFalse(path.exists())

    def test_other_instance_cannot_read_or_publish_while_a_session_owns_the_job(self):
        owner = self.create()
        other = TaskForge(self.root / "job")
        with owner.session(self.grader, evaluator_id="arithmetic-v1"):
            self.assertEqual(owner.status()["completed_tasks"], 0)
            self.assertEqual(owner.assemble()["completed_tasks"], 0)
            with self.assertRaisesRegex(RuntimeError, "active local delivery session"):
                other.status()
            with self.assertRaisesRegex(RuntimeError, "active local delivery session"):
                other.assemble()
        self.assertEqual(other.status()["completed_tasks"], 0)
        self.assertEqual(other.assemble()["completed_tasks"], 0)


if __name__ == "__main__":
    unittest.main()
