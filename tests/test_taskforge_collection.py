"""TaskForge's local transport, assignment binding and evidence-only assembly."""

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
from unittest.mock import Mock, patch

from taskforge.assembly import assemble_library
import taskforge.collection as collection_module
from taskforge.collection import ResultCollector


TASKS = [
    {"task_id": "unit-double", "function_name": "double", "signature": "double(value)",
     "description": "Return twice the numeric input.", "examples": [{"input": 3, "output": 6}]},
    {"task_id": "unit-square", "function_name": "square", "signature": "square(value)",
     "description": "Return the square of the numeric input.", "examples": [{"input": 3, "output": 9}]},
]
SOURCES = {
    "unit-double": "def double(value):\n    return value * 2\n",
    "unit-square": "def square(value):\n    return value * value\n",
}


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class TaskForgeCollectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="forge-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tasks = copy.deepcopy(TASKS)
        self.assignments = [{"id": "assignment-" + str(index), "task": task}
                            for index, task in enumerate(self.tasks)]
        self.grader = Mock(side_effect=lambda task, source: {
            "passed": source == SOURCES[task["task_id"]], "tests_run": 1,
            "private_grader_detail": "This belongs only in stored grading evidence",
        })

    def collector(self):
        collector = ResultCollector(self.root / "state", self.assignments, self.grader)
        self.addCleanup(collector.close)
        return collector

    def post(self, path, payload, route="/submit"):
        connection = UnixConnection(path)
        try:
            connection.request("POST", route, json.dumps(payload).encode(), {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_real_unix_http_binds_grader_and_receipt_to_registered_assignment(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("real-run", "assignment-0", path)
        # All payload identity fields apart from the checked task_id are inert.
        status, response = self.post(path, {
            "task_id": "unit-double", "source_code": SOURCES["unit-double"],
            "run_id": "spoofed-run", "case_id": "assignment-1", "assignment_id": "assignment-1",
            "task": self.tasks[1],
        })
        self.assertEqual(status, 200)
        self.assertTrue(response["accepted"])
        self.assertTrue(response["valid"])
        self.assertEqual(set(response), {"receipt_id", "accepted", "valid", "task_id"})
        self.grader.assert_called_once_with(self.tasks[0], SOURCES["unit-double"])
        self.assertNotIn("private_grader_detail", response)
        receipt = collector.get_receipts("real-run")[0]
        self.assertEqual(receipt["case_id"], "assignment-0")
        self.assertEqual(receipt["run_id"], "real-run")
        self.assertEqual(receipt["receipt_id"], response["receipt_id"])
        self.assertEqual(receipt["source_sha256"], hashlib.sha256(SOURCES["unit-double"].encode()).hexdigest())
        self.assertEqual(receipt["transport"], "HTTP over workspace Unix socket")
        self.assertEqual(collector.get_receipts("spoofed-run"), [])
        saved = json.loads((self.root / "state/receipts.jsonl").read_text())
        self.assertEqual(saved, receipt)
        receipt["source_code"] = "outside mutation"
        self.assertEqual(collector.get_receipts("real-run")[0]["source_code"], SOURCES["unit-double"])

    def test_submitting_another_task_cannot_select_the_grader_binding(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        status, response = self.post(path, {"task_id": "unit-square", "source_code": SOURCES["unit-square"]})
        self.assertEqual(status, 200)
        self.assertFalse(response["valid"])
        self.grader.assert_not_called()
        receipt = collector.get_receipts("run")[0]
        self.assertEqual(receipt["case_id"], "assignment-0")
        self.assertFalse(receipt["valid"])
        self.assertEqual(collector.aggregate()["completed_tasks"], 0)

    def test_registered_task_is_not_mutated_by_caller_or_callback(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        self.assignments[0]["task"]["task_id"] = "changed-outside"
        tasks_seen = []

        def grader(task, source):
            tasks_seen.append(task["task_id"])
            task["task_id"] = "changed-inside-callback"
            return {"passed": True}

        collector.grader = grader
        for _ in range(2):
            status, response = self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
            self.assertEqual(status, 200)
            self.assertTrue(response["valid"])
        self.assertEqual(tasks_seen, ["unit-double", "unit-double"])
        self.assertEqual(collector.assignments["assignment-0"]["task"]["task_id"], "unit-double")

    def test_restart_retains_receipts_registration_and_first_valid_source(self):
        path = self.root / "workspace.sock"
        with ResultCollector(self.root / "state", self.assignments, self.grader) as first:
            first.register_run("run", "assignment-0", path)
            self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
            before = first.get_receipts("run")
        with ResultCollector(self.root / "state", self.assignments, self.grader) as restarted:
            restarted.register_run("run", "assignment-0", path)
            self.assertEqual(restarted.get_receipts("run"), before)
            self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
            library = restarted.aggregate()
            self.assertEqual(library["submission_count"], 2)
            self.assertEqual(library["valid_submissions"], 2)
            self.assertEqual(library["completed_tasks"], 1)
            self.assertEqual(library["task_results"][0]["receipt_id"], before[0]["receipt_id"])
            with self.assertRaisesRegex(ValueError, "different case"):
                restarted.register_run("run", "assignment-1", self.root / "other.sock")
        registrations = (self.root / "state/registrations.jsonl").read_text().splitlines()
        self.assertEqual(len(registrations), 1)
        self.assertEqual(set(json.loads(registrations[0])), {"run_id", "case_id", "socket_path", "block_delivery"})
        self.assertFalse(path.exists())

    def test_blocked_receiver_records_arrival_but_cannot_accept_or_grade(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path, block_delivery=True)
        status, response = self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
        self.assertEqual(status, 403)
        self.assertFalse(response["accepted"])
        self.assertFalse(response["valid"])
        self.grader.assert_not_called()
        self.assertEqual(collector.get_receipts("run"), [])
        self.assertEqual(len(collector.get_blocked("run")), 1)
        journal = json.loads((self.root / "state/received.jsonl").read_text())
        self.assertTrue(journal["blocked"])
        self.assertEqual(journal["registered_task_id"], "unit-double")
        self.assertEqual(journal["source_code"], SOURCES["unit-double"])
        self.assertEqual(journal["receipt_id"], response["receipt_id"])
        self.assertEqual(collector.all_receipts(), [])
        self.assertFalse(collector.aggregate()["large_task_complete"])

    def test_grader_exception_preserves_received_source_as_failed_receipt(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        self.grader.side_effect = RuntimeError("synthetic evaluator failure")
        status, response = self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
        self.assertEqual(status, 200)
        self.assertTrue(response["accepted"])
        self.assertFalse(response["valid"])
        receipt = collector.get_receipts("run")[0]
        self.assertEqual(receipt["source_code"], SOURCES["unit-double"])
        self.assertEqual(receipt["source_sha256"], hashlib.sha256(SOURCES["unit-double"].encode()).hexdigest())
        self.assertEqual(receipt["grade"], {"passed": False, "error": "Grader failed: RuntimeError"})
        self.assertEqual(json.loads((self.root / "state/receipts.jsonl").read_text()), receipt)
        journal = json.loads((self.root / "state/received.jsonl").read_text())
        self.assertEqual(journal["receipt_id"], receipt["receipt_id"])
        self.assertEqual(journal["source_code"], receipt["source_code"])
        self.assertEqual(journal["source_sha256"], receipt["source_sha256"])
        self.assertNotIn("valid", journal)
        self.assertNotIn("grade", journal)
        self.assertEqual(collector.aggregate()["completed_tasks"], 0)

    def test_non_boolean_or_non_serializable_grader_verdicts_are_failed_receipts(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        invalid = [None, [], "passed", {}, {"passed": None}, {"passed": "false"},
                   {"passed": "true"}, {"passed": 0}, {"passed": 1}, {"passed": []},
                   {"passed": True, "detail": object()}, {"passed": True, "score": float("nan")}]
        self.grader.side_effect = None
        for verdict in invalid:
            with self.subTest(verdict=verdict):
                self.grader.return_value = verdict
                status, response = self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
                self.assertEqual(status, 200)
                self.assertTrue(response["accepted"])
                self.assertFalse(response["valid"])
                receipt = collector.get_receipts("run")[-1]
                self.assertIs(receipt["grade"]["passed"], False)
                self.assertTrue(receipt["grade"]["error"].startswith("Grader failed:"))
                self.assertEqual(receipt["source_code"], SOURCES["unit-double"])
                self.assertEqual(set(receipt), {"receipt_id", "received_at", "run_id", "case_id", "task_id",
                                               "source_code", "source_sha256", "valid", "grade", "blocked", "transport"})
        self.assertEqual(len(collector.all_receipts()), len(invalid))
        self.assertEqual(len((self.root / "state/received.jsonl").read_text().splitlines()), len(invalid))
        self.assertEqual(len((self.root / "state/receipts.jsonl").read_text().splitlines()), len(invalid))
        self.assertEqual(collector.aggregate()["completed_tasks"], 0)

    def test_all_receipts_returns_detached_snapshots_across_runs(self):
        collector = self.collector()
        self.assertEqual(collector.all_receipts(), [])
        for index, task in enumerate(self.tasks):
            path = self.root / ("run-" + str(index) + ".sock")
            collector.register_run("run-" + str(index), "assignment-" + str(index), path)
            self.post(path, {"task_id": task["task_id"], "source_code": SOURCES[task["task_id"]]})
        snapshot = collector.all_receipts()
        self.assertEqual({item["run_id"] for item in snapshot}, {"run-0", "run-1"})
        snapshot[0]["grade"]["passed"] = False
        snapshot[0]["source_code"] = "caller mutation"
        snapshot.clear()
        fresh = collector.all_receipts()
        self.assertEqual(len(fresh), 2)
        self.assertTrue(all(item["grade"]["passed"] for item in fresh))
        self.assertEqual(fresh[0]["source_code"], SOURCES["unit-double"])

    def test_process_exit_during_grading_retains_ungraded_source_without_accepting_it(self):
        state = self.root / "crashed-state"
        path = self.root / "crashed.sock"
        child_code = """
import json, os, sys, threading
from pathlib import Path
from taskforge.collection import ResultCollector
def crash(task, source):
    os._exit(23)
collector = ResultCollector(Path(sys.argv[1]), json.loads(sys.argv[3]), crash)
collector.register_run('crashed-run', 'assignment-0', Path(sys.argv[2]))
print('READY', flush=True)
threading.Event().wait()
"""
        child = subprocess.Popen([sys.executable, "-u", "-c", child_code, str(state), str(path),
                                  json.dumps(self.assignments)], cwd=Path(__file__).resolve().parents[1],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def cleanup():
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

        self.addCleanup(cleanup)
        self.assertTrue(select.select([child.stdout], [], [], 5)[0], "Collector child did not start")
        self.assertEqual(child.stdout.readline().strip(), "READY")
        with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError)):
            self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
        self.assertEqual(child.wait(timeout=5), 23)
        journal = json.loads((state / "received.jsonl").read_text())
        self.assertEqual(journal["schema_version"], 1)
        self.assertEqual(journal["registered_task_id"], "unit-double")
        self.assertEqual(journal["run_id"], "crashed-run")
        self.assertEqual(journal["case_id"], "assignment-0")
        self.assertEqual(journal["source_code"], SOURCES["unit-double"])
        self.assertEqual(journal["source_sha256"], hashlib.sha256(SOURCES["unit-double"].encode()).hexdigest())
        self.assertNotIn("valid", journal)
        self.assertNotIn("grade", journal)
        self.assertFalse((state / "receipts.jsonl").exists())
        with ResultCollector(state, self.assignments, self.grader) as restarted:
            self.assertEqual(restarted.all_receipts(), [])
            self.assertEqual(restarted.aggregate()["completed_tasks"], 0)
        self.grader.assert_not_called()

    def test_close_waits_until_an_accepted_request_finishes_grading_and_persistence(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        grading_started, release_grader, close_finished, second_close_finished = (threading.Event() for _ in range(4))

        def grader(task, source):
            grading_started.set()
            if not release_grader.wait(timeout=4):
                raise RuntimeError("test grader was not released")
            return {"passed": True}

        def close():
            collector.close_run("run")
            close_finished.set()

        def close_again():
            collector.close_run("run")
            second_close_finished.set()

        collector.grader = grader
        with ThreadPoolExecutor(max_workers=3) as pool:
            request = pool.submit(self.post, path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
            try:
                self.assertTrue(grading_started.wait(timeout=2))
                closing = pool.submit(close)
                self.assertFalse(close_finished.wait(timeout=0.15))
                second_closing = pool.submit(close_again)
                self.assertFalse(second_close_finished.wait(timeout=0.15))
                self.assertEqual(collector.get_receipts("run"), [])
                self.assertEqual(collector.all_receipts(), [])
                journal = json.loads((self.root / "state/received.jsonl").read_text())
                self.assertEqual(journal["source_code"], SOURCES["unit-double"])
                self.assertEqual(journal["registered_task_id"], "unit-double")
                self.assertNotIn("grade", journal)
            finally:
                release_grader.set()
            status, response = request.result(timeout=3)
            closing.result(timeout=3)
            second_closing.result(timeout=3)
        self.assertEqual(status, 200)
        self.assertTrue(response["valid"])
        self.assertTrue(close_finished.is_set())
        self.assertTrue(second_close_finished.is_set())
        self.assertEqual(len(collector.get_receipts("run")), 1)
        self.assertEqual(response["receipt_id"], journal["receipt_id"])
        self.assertEqual(collector.aggregate()["completed_tasks"], 1)
        self.assertFalse(path.exists())

    def test_concurrent_registration_cannot_create_two_receivers_for_one_run(self):
        collector = self.collector()
        constructing, release, second_finished = (threading.Event() for _ in range(3))
        server_type = collection_module._UnixHTTPServer

        def make_server(*args, **kwargs):
            constructing.set()
            if not release.wait(timeout=4):
                raise RuntimeError("test server construction was not released")
            return server_type(*args, **kwargs)

        def second_registration():
            try:
                collector.register_run("run", "assignment-0", self.root / "second.sock")
            finally:
                second_finished.set()

        with patch("taskforge.collection._UnixHTTPServer", side_effect=make_server) as factory:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(collector.register_run, "run", "assignment-0", self.root / "first.sock")
                try:
                    self.assertTrue(constructing.wait(timeout=2))
                    second = pool.submit(second_registration)
                    self.assertFalse(second_finished.wait(timeout=0.15))
                finally:
                    release.set()
                first.result(timeout=3)
                with self.assertRaisesRegex(ValueError, "already registered"):
                    second.result(timeout=3)
            self.assertEqual(factory.call_count, 1)
        self.assertTrue((self.root / "first.sock").is_socket())
        self.assertFalse((self.root / "second.sock").exists())
        collector.close()
        self.assertFalse((self.root / "first.sock").exists())

    def test_close_does_not_unlink_a_file_or_symlink_replacing_its_socket(self):
        collector = self.collector()
        outside = self.root / "outside-file"
        outside.write_text("unrelated content")
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind):
                path = self.root / (kind + ".sock")
                collector.register_run("run-" + kind, "assignment-0", path)
                path.unlink()
                if kind == "file":
                    path.write_text("replacement content")
                else:
                    path.symlink_to(outside)
                collector.close_run("run-" + kind)
                if kind == "file":
                    self.assertEqual(path.read_text(), "replacement content")
                else:
                    self.assertTrue(path.is_symlink())
                    self.assertEqual(outside.read_text(), "unrelated content")

    def test_failed_receiver_thread_start_releases_socket_and_allows_a_retry(self):
        collector = self.collector()
        path = self.root / "workspace.sock"
        with patch("taskforge.collection.threading.Thread.start", side_effect=RuntimeError("synthetic thread exhaustion")):
            with self.assertRaisesRegex(RuntimeError, "thread exhaustion"):
                collector.register_run("run", "assignment-0", path)
        self.assertFalse(path.exists())
        # No unstarted receiver may survive and block shutdown forever.
        collector.close()
        collector.register_run("run", "assignment-0", path)
        status, response = self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
        self.assertEqual(status, 200)
        self.assertTrue(response["valid"])

    def test_assembly_has_no_gold_fallback_and_preserves_received_code_exactly(self):
        collector = self.collector()
        # A reference-looking field must never be used as an implementation.
        tasks = copy.deepcopy(self.tasks)
        tasks[1]["reference_code"] = SOURCES["unit-square"]
        empty = assemble_library(tasks, [], self.root / "empty-library")
        self.assertEqual(empty["completed_tasks"], 0)
        self.assertFalse((self.root / "empty-library/square.py").exists())
        path = self.root / "workspace.sock"
        collector.register_run("run", "assignment-0", path)
        self.post(path, {"task_id": "unit-double", "source_code": SOURCES["unit-double"]})
        receipts = collector.get_receipts("run")
        result = assemble_library(tasks, receipts, self.root / "library")
        self.assertEqual(result["total_tasks"], 2)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertFalse(result["large_task_complete"])
        self.assertEqual((self.root / "library/double.py").read_text(), SOURCES["unit-double"])
        self.assertEqual((self.root / "library/__init__.py").read_text(), "from .double import double\n")
        self.assertFalse((self.root / "library/square.py").exists())
        self.assertNotIn("source_code", result["task_results"][1])
        # Rebuilding from no accepted evidence removes an obsolete known module.
        assemble_library(tasks, [], self.root / "library")
        self.assertFalse((self.root / "library/double.py").exists())

    def test_unsafe_task_ids_module_names_and_duplicate_outputs_are_rejected(self):
        invalid = []
        for name in ("../escape", "sub/name", "__init__", "bad-name", "class", "a\nb"):
            invalid.append([{**self.tasks[0], "function_name": name}])
        for task_id in ("../task", "/absolute", "a/b", "", "task\x00"):
            invalid.append([{**self.tasks[0], "task_id": task_id}])
        invalid.extend(([self.tasks[0], copy.deepcopy(self.tasks[0])],
                        [self.tasks[0], {**self.tasks[1], "function_name": "double"}]))
        for tasks in invalid:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                assemble_library(tasks, [], self.root / "invalid-library")
        self.assertFalse((self.root / "invalid-library").exists())
        with self.assertRaises(ValueError):
            ResultCollector(self.root / "bad-state", [{"id": "bad", "task": {**self.tasks[0], "function_name": "__init__"}}], self.grader)
        self.assertFalse((self.root / "bad-state").exists())

    def test_assembly_refuses_existing_symlink_outputs(self):
        outside = self.root / "outside.py"
        outside.write_text("untouched")
        library = self.root / "library"
        library.mkdir()
        (library / "__init__.py").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            assemble_library(self.tasks, [], library)
        self.assertEqual(outside.read_text(), "untouched")
        (library / "__init__.py").unlink()
        (library / "double.py").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            assemble_library(self.tasks, [], library)
        self.assertEqual(outside.read_text(), "untouched")

    def test_reassembly_replaces_the_full_module_inventory(self):
        receipts = [{"task_id": task["task_id"], "source_code": SOURCES[task["task_id"]],
                     "source_sha256": hashlib.sha256(SOURCES[task["task_id"]].encode()).hexdigest(),
                     "receipt_id": "receipt-" + task["task_id"], "run_id": "run", "valid": True}
                    for task in self.tasks]
        library = self.root / "library"
        assemble_library(self.tasks, receipts, library)
        (library / "orphan.py").write_text("# stale module")
        (library / "stale_package").mkdir()
        (library / "stale_package/__init__.py").write_text("# stale nested package")
        rebuilt = assemble_library(self.tasks[:1], receipts[:1], library)
        self.assertEqual(rebuilt["completed_tasks"], 1)
        self.assertEqual({item.name for item in library.iterdir()}, {"__init__.py", "double.py"})
        self.assertEqual((library / "double.py").read_text(), SOURCES["unit-double"])
        self.assertEqual((library / "__init__.py").read_text(), "from .double import double\n")

    def test_failed_staging_publish_restores_previous_library(self):
        library = self.root / "library"
        library.mkdir()
        (library / "__init__.py").write_text("# previously published package\n")
        (library / "previous.py").write_text("# preserved until successful publish\n")
        import os
        original_replace = os.replace

        def fail_publish(source, destination):
            if Path(source).name == "package":
                raise OSError("synthetic publish failure")
            return original_replace(source, destination)

        with patch("taskforge.assembly.os.replace", side_effect=fail_publish):
            with self.assertRaisesRegex(OSError, "publish failure"):
                assemble_library(self.tasks, [], library)
        self.assertEqual((library / "__init__.py").read_text(), "# previously published package\n")
        self.assertEqual((library / "previous.py").read_text(), "# preserved until successful publish\n")
        self.assertFalse(list(self.root.glob(".taskforge-assembly-*")))


if __name__ == "__main__":
    unittest.main()
