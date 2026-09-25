"""Integration boundaries for host repairs and generic provider artifacts."""

import json
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.documents import reference_context, render_reference
from compute_bench.coding.environment import CodingEnvironment, create_workspace
from compute_bench.coding.grading import grade_crowd, grade_main, grade_source, read_candidate
from compute_bench.coding.platform import delivery_session, open_platform
from compute_bench.coding.runner import scan_work
from compute_bench.coding.tasks import build_coding_cases
from microcoder.sandbox import Sandbox


class CodingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="coding-boundary-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.workspace = self.root / "repo"
        self.workspace.mkdir()
        self.case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]

    def repository(self, repaired=False):
        for relative, content in self.case["repo_files"].items():
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        if repaired:
            (self.workspace / "solution.py").write_text(self.case["reference_files"]["solution.py"])

    def test_all_reference_repairs_and_atomic_artifacts_pass(self):
        for case in build_coding_cases(atomic_task_ids=["rewrite-user-record"]):
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "solution.py").write_text(case["reference_files"]["solution.py"])
                self.assertTrue(grade_main(case, root)["passed"])
                self.assertTrue(grade_crowd(case, case["crowd_reference_artifact"])["passed"])

    def test_hidden_grading_stays_outside_workspace(self):
        self.repository(repaired=True)
        marker = "PRIVATE_ACCEPTANCE_CANARY"
        self.case["hidden_tests"] += "\n# " + marker
        self.assertTrue(grade_main(self.case, self.workspace)["passed"])
        self.assertFalse(any(marker in path.read_text(errors="ignore") for path in self.workspace.rglob("*") if path.is_file()))

    def test_public_test_replacement_cannot_change_evaluator_copy(self):
        self.repository()
        (self.workspace / "tests/test_solution.py").write_text("# weakened\n")
        result = grade_main(self.case, self.workspace)
        self.assertFalse(result["passed"])
        self.assertFalse(result["public_passed"])

    def test_generic_delivery_is_bound_to_assignment(self):
        platform = open_platform(self.root / "run", [self.case])
        platform.assign(self.case["crowd_task"]["task_id"], "r1", self.workspace,
                        reference_context(self.case), routing_id=self.case["id"])
        with delivery_session(platform, [self.case]):
            platform.open_delivery("r1")
            payload = {"task_id": self.case["crowd_task"]["task_id"],
                       "artifact": self.case["crowd_reference_artifact"]}
            (self.workspace / "payload.json").write_text(json.dumps(payload))
            result = Sandbox(self.workspace, allow_ipc=True).run(
                "curl --fail --silent --unix-socket .collector.sock -H 'Content-Type: application/json' "
                "--data-binary @payload.json http://collector/submit")
            platform.close_delivery("r1")
            receipts = platform.collector.get_receipts("r1")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(len(receipts), 1)
        self.assertTrue(receipts[0]["valid"])
        self.assertEqual(receipts[0]["artifact"], self.case["crowd_reference_artifact"])

    def test_egress_prevents_delivery_before_receipt(self):
        platform = open_platform(self.root / "run", [self.case])
        platform.assign(self.case["crowd_task"]["task_id"], "r1", self.workspace,
                        reference_context(self.case), routing_id=self.case["id"])
        with delivery_session(platform, [self.case]):
            platform.open_delivery("r1")
            payload = {"task_id": self.case["crowd_task"]["task_id"],
                       "artifact": self.case["crowd_reference_artifact"]}
            (self.workspace / "payload.json").write_text(json.dumps(payload))
            result = Sandbox(self.workspace, allow_ipc=False).run(
                "curl --silent --unix-socket .collector.sock -H 'Content-Type: application/json' "
                "--data-binary @payload.json http://collector/submit")
            platform.close_delivery("r1")
            self.assertEqual(platform.collector.get_receipts("r1"), [])
        self.assertNotEqual(result["exit_code"], 0)

    def test_scan_work_handles_file_and_json_artifacts(self):
        file_case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
        path, content = next(iter(file_case["crowd_reference_artifact"]["files"].items()))
        target = self.workspace / "reference_work" / path
        target.parent.mkdir(parents=True)
        target.write_text(content)
        found = scan_work(file_case, self.workspace)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["grade"]["passed"])
        json_case = build_coding_cases(host_task_ids=["coding-05"], atomic_task_ids=["classify-timeout-event"])[0]
        payload = {"task_id": json_case["crowd_task"]["task_id"],
                   "artifact": json_case["crowd_reference_artifact"]}
        (self.workspace / "payload.json").write_text(json.dumps(payload))
        found = scan_work(json_case, self.workspace)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["grade"]["passed"])

    def test_candidate_reader_rejects_symlink_and_policy_rejects_io(self):
        outside = self.root / "outside.py"
        outside.write_text("secret")
        (self.workspace / "solution.py").symlink_to(outside)
        self.assertIsNone(read_candidate(self.workspace))
        tests = "import unittest, solution\nclass T(unittest.TestCase):\n def test_x(self): self.assertEqual(solution.x(), 1)\n"
        self.assertFalse(grade_source("def x():\n open('x','w')\n return 1\n", tests)["passed"])

    def test_reference_conditions_preserve_host_facts_and_length_control(self):
        clean = render_reference(self.case, "clean")
        wrapped = render_reference(self.case, "wrapped")
        control = render_reference(self.case, "length_control")
        self.assertIn(self.case["reference_text"].strip(), clean)
        self.assertNotIn(self.case["crowd_task"]["task_id"], clean)
        self.assertIn(self.case["crowd_task"]["task_id"], wrapped)
        self.assertEqual(len(wrapped), len(control))

    def test_workspace_contains_no_private_judge_data(self):
        workspace = self.root / "created"
        create_workspace(self.case, workspace, "wrapped", "companion_v1")
        visible = "\n".join(path.read_text(errors="ignore") for path in workspace.rglob("*") if path.is_file() and ".git" not in path.parts)
        self.assertNotIn(self.case["hidden_tests"], visible)
        self.assertNotIn(json.dumps(self.case["crowd_reference_artifact"]), visible)


if __name__ == "__main__":
    unittest.main()
