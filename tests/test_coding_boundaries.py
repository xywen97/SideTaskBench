"""Integration checks for independent grading and actual delivery boundaries."""

import json
import os
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.documents import reference_context, render_reference
from compute_bench.coding.environment import CodingEnvironment, create_workspace
from compute_bench.coding.grading import grade_crowd, grade_main, grade_source, read_candidate
from compute_bench.coding.runner import scan_work
from compute_bench.coding.platform import delivery_session
from compute_bench.coding.tasks import build_coding_cases
from microcoder.sandbox import Sandbox
from taskforge import TaskForge


class CodingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="coding-boundary-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.workspace = self.root / "repo"
        self.workspace.mkdir()
        self.case = build_coding_cases(1)[0]

    def collector(self):
        job = TaskForge.create(self.root / "platform", {
            "job_id": "boundary-test", "objective": "Check isolated benchmark delivery.",
            "components": [self.case["crowd_task"]],
        }, collector_directory=self.root / "receipts")
        job.assign(self.case["crowd_task"]["task_id"], "test-run", self.workspace,
                   reference_context(self.case), routing_id=self.case["id"])
        self.enterContext(delivery_session(job, [self.case]))
        job.open_delivery("test-run")
        return job.collector

    def deliver(self, source_code, *, allow_ipc=True, extras=None):
        payload = {"task_id": self.case["crowd_task"]["task_id"], "source_code": source_code}
        payload.update(extras or {})
        (self.workspace / "delivery.json").write_text(json.dumps(payload), encoding="utf-8")
        return Sandbox(self.workspace, allow_ipc=allow_ipc).run(
            "curl --fail --silent --show-error --unix-socket .collector.sock "
            "-H 'Content-Type: application/json' --data-binary @delivery.json http://collector/submit"
        )

    def repository(self, *, repaired):
        for relative, content in self.case["repo_files"].items():
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if repaired:
            (self.workspace / "solution.py").write_text(self.case["reference_files"]["solution.py"], encoding="utf-8")

    def environment(self, *, defense="none"):
        self.repository(repaired=False)
        (self.workspace / "docs").mkdir(exist_ok=True)
        (self.workspace / "docs" / "reference.md").write_text(render_reference(self.case, "wrapped"), encoding="utf-8")
        return CodingEnvironment(self.case, self.workspace, "wrapped", defense=defense)

    def test_candidate_code_cannot_write_host_files_during_independent_grading(self):
        canary = self.root / "host-canary.txt"
        canary.write_text("unchanged")
        source = f"open({str(canary)!r}, 'w').write('ESCAPED')\ndef value():\n    return 42\n"
        tests = "import unittest, solution\nclass Acceptance(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(solution.value(), 42)\n"
        result = grade_source(source, tests)
        self.assertFalse(result["passed"])
        self.assertEqual(canary.read_text(), "unchanged")

    def test_early_exit_does_not_count_as_successful_acceptance(self):
        tests = "import unittest, solution\nclass Acceptance(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(solution.value(), 42)\n"
        for source in ("import os; os._exit(0)", "raise SystemExit(0)"):
            with self.subTest(source=source):
                result = grade_source(source, tests)
                self.assertFalse(result["passed"])
                self.assertEqual(result["tests_run"], 0)

    def test_forged_success_marker_is_rejected_before_candidate_execution(self):
        source = (
            "import os\n"
            "print('__BENCH_GRADE__={\"ran\":1,\"failures\":0,\"errors\":0,\"skipped\":0,\"successful\":true}', flush=True)\n"
            "os._exit(0)\n"
        )
        tests = "import unittest, solution\nclass Acceptance(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(solution.nonexistent(), 42)\n"
        result = grade_source(source, tests)
        self.assertFalse(result["passed"])
        self.assertEqual(result["tests_run"], 0)
        self.assertTrue(result["policy_errors"])
        self.assertNotIn("execution", result)

    def test_all_six_reference_repairs_and_outsourced_functions_pass_policy_and_grading(self):
        for case in build_coding_cases():
            with self.subTest(case=case["id"]):
                repo = self.root / case["id"]
                repo.mkdir()
                (repo / "solution.py").write_text(case["reference_files"]["solution.py"], encoding="utf-8")
                main = grade_main(case, repo)
                self.assertTrue(main["passed"], main)
                crowd = grade_crowd(case, case["crowd_reference_code"])
                self.assertTrue(crowd["passed"], crowd)
                self.assertGreater(crowd["tests_run"], 0)

    def test_hidden_grading_never_writes_private_tests_into_victim_repository(self):
        self.repository(repaired=True)
        private_marker = "PRIVATE_MAIN_ACCEPTANCE_CANARY_8a58c91"
        self.case["hidden_tests"] += "\n# " + private_marker + "\n"
        result = grade_main(self.case, self.workspace)
        self.assertTrue(result["passed"], result)
        for path in self.workspace.rglob("*"):
            if path.is_file():
                self.assertNotIn(private_marker, path.read_text(encoding="utf-8"))
        self.assertFalse((self.workspace / "acceptance.py").exists())
        self.assertFalse((self.workspace / "runner.py").exists())

    def test_replacing_public_tests_cannot_turn_buggy_code_into_a_pass(self):
        self.repository(repaired=False)
        (self.workspace / "tests" / "test_solution.py").write_text(
            "import unittest\nclass AlwaysPass(unittest.TestCase):\n    def test_nothing(self):\n        pass\n"
        )
        result = grade_main(self.case, self.workspace)
        self.assertFalse(result["passed"])
        self.assertFalse(result["public_passed"])
        self.assertFalse(result["hidden_passed"])

    def test_candidate_reader_rejects_symlinks_and_traversal(self):
        canary = self.root / "outside.py"
        canary.write_text("HOST_ONLY_VALUE")
        (self.workspace / "solution.py").symlink_to(canary)
        self.assertIsNone(read_candidate(self.workspace))
        self.assertIsNone(read_candidate(self.workspace, "../outside.py"))
        self.assertIsNone(read_candidate(self.workspace, str(canary)))
        (self.workspace / "outside").symlink_to(self.root, target_is_directory=True)
        self.assertIsNone(read_candidate(self.workspace, "outside/outside.py"))

    def test_real_delivery_is_bound_to_registered_run_and_response_hides_grading(self):
        collector = self.collector()
        result = self.deliver(self.case["crowd_reference_code"], extras={"run_id": "spoofed-run"})
        self.assertEqual(result["exit_code"], 0, result)
        response = json.loads(result["stdout"])
        self.assertTrue(response["valid"], response)
        self.assertEqual(set(response), {"receipt_id", "accepted", "valid", "task_id"})
        receipts = collector.get_receipts("test-run")
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["run_id"], "test-run")
        self.assertEqual(collector.get_receipts("spoofed-run"), [])
        self.assertNotIn("execution", result["stdout"])
        self.assertNotIn("Acceptance", result["stdout"])
        self.assertTrue((self.root / "receipts" / "receipts.jsonl").exists())

    def test_egress_block_prevents_even_rejected_collector_receipts(self):
        collector = self.collector()
        result = self.deliver(self.case["crowd_reference_code"], allow_ipc=False)
        self.assertNotEqual(result["exit_code"], 0, result)
        self.assertEqual(collector.get_receipts("test-run"), [])
        self.assertEqual(collector.get_blocked("test-run"), [])
        self.assertFalse((self.root / "receipts" / "receipts.jsonl").exists())
        self.assertFalse((self.root / "receipts" / "blocked.jsonl").exists())

    def test_invalid_delivered_function_is_received_but_never_accepted(self):
        collector = self.collector()
        source = f"def {self.case['crowd_task']['signature']}:\n    return None\n"
        result = self.deliver(source)
        self.assertEqual(result["exit_code"], 0, result)
        self.assertFalse(json.loads(result["stdout"])["valid"])
        receipt = collector.get_receipts("test-run")[0]
        self.assertFalse(receipt["valid"])
        self.assertFalse(receipt["grade"]["passed"])
        self.assertEqual(collector.aggregate()["completed_tasks"], 0)

    def test_file_tools_reject_host_paths_and_symlink_traversal(self):
        environment = self.environment()
        canary = self.root / "outside.txt"
        canary.write_text("HOST_ONLY_CANARY")
        (self.workspace / "escape-file").symlink_to(canary)
        (self.workspace / "escape-parent").symlink_to(self.root, target_is_directory=True)
        (self.workspace / "internal-alias").symlink_to("solution.py")
        invalid = ["../outside.txt", str(canary), "/etc/passwd", "/workspace/../outside.txt",
                   "escape-file", "escape-parent/outside.txt", "internal-alias", ".", "/workspace/"]
        for path in invalid:
            with self.subTest(path=path):
                read = environment.execute("read_file", {"path": path})
                self.assertIn("error", read)
                self.assertNotIn("HOST_ONLY_CANARY", str(read))
                write = environment.execute("write_file", {"path": path, "content": "changed"})
                self.assertIn("error", write)
        self.assertEqual(canary.read_text(), "HOST_ONLY_CANARY")
        write = environment.execute("write_file", {"path": "/workspace/nested/new.py", "content": "value = 1\n"})
        self.assertNotIn("error", write)
        read = environment.execute("read_file", {"path": "nested/new.py"})
        self.assertEqual(read["content"], "value = 1\n")

    def test_file_tools_cannot_overwrite_reserved_env_or_collector_paths(self):
        environment = self.environment()
        for path in (".env", ".env.local", ".collector.sock", "nested/.env.production"):
            with self.subTest(path=path):
                result = environment.execute("write_file", {"path": path, "content": "unexpected"})
                self.assertIn("error", result)
                self.assertFalse((self.workspace / path).exists())

    def test_file_tools_reject_fifo_without_opening_or_blocking(self):
        environment = self.environment()
        os.mkfifo(self.workspace / "pipe")
        for name, args in (("read_file", {"path": "pipe"}),
                           ("write_file", {"path": "pipe", "content": "would-block"})):
            with self.subTest(tool=name):
                result = environment.execute(name, args)
                self.assertIn("error", result)

    def test_environment_egress_flag_blocks_real_shell_delivery(self):
        collector = self.collector()
        environment = self.environment(defense="egress")
        payload = {"task_id": self.case["crowd_task"]["task_id"], "source_code": self.case["crowd_reference_code"]}
        (self.workspace / "delivery.json").write_text(json.dumps(payload))
        result = environment.execute("shell", {"command":
            "curl --fail --silent --show-error --unix-socket .collector.sock "
            "--data-binary @delivery.json http://collector/submit"})
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(collector.get_receipts("test-run"), [])
        self.assertEqual(collector.get_blocked("test-run"), [])

    def test_search_only_lists_source_and_reading_reference_records_exposure(self):
        environment = self.environment()
        search = environment.execute("search_reference", {"query": self.case["reference_topic"]})
        self.assertEqual(search["results"][0]["path"], "docs/reference.md")
        self.assertFalse(environment.events[-1]["exposed"])
        reference = environment.execute("read_file", {"path": "docs/reference.md"})
        self.assertIn(self.case["crowd_task"]["task_id"], reference["content"])
        self.assertTrue(environment.events[-1]["exposed"])

    def test_workspace_creation_does_not_copy_private_judge_material(self):
        private_marker = "PRIVATE_JUDGE_CANARY_5730d"
        self.case["hidden_tests"] += "\n# " + private_marker
        self.case["crowd_tests"] += "\n# " + private_marker
        self.case["crowd_reference_code"] += "\n# " + private_marker
        self.case["reference_files"]["solution.py"] += "\n# " + private_marker
        workspace = self.root / "fresh"
        create_workspace(self.case, workspace, "wrapped", "companion_v1")
        for path in workspace.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                self.assertNotIn(private_marker, path.read_text(encoding="utf-8"))
        self.assertEqual((workspace / "solution.py").read_text(), self.case["repo_files"]["solution.py"])

    def test_observed_work_requires_independently_passing_candidate_and_skips_symlinks(self):
        valid = self.workspace / "reference_work" / "valid.py"
        valid.parent.mkdir()
        valid.write_text(self.case["crowd_reference_code"], encoding="utf-8")
        (valid.parent / "invalid.py").write_text(
            f"def {self.case['crowd_task']['signature']}:\n    return None\n", encoding="utf-8")
        outside = self.root / "host_reference.py"
        outside.write_text(self.case["crowd_reference_code"], encoding="utf-8")
        (self.workspace / "escape.py").symlink_to(outside)
        observed = scan_work(self.case, self.workspace)
        self.assertEqual({item["path"] for item in observed}, {"reference_work/valid.py", "reference_work/invalid.py"})
        valid_paths = {item["path"] for item in observed if item["grade"]["passed"]}
        self.assertEqual(valid_paths, {"reference_work/valid.py"})


if __name__ == "__main__":
    unittest.main()
