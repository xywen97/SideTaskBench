"""Recover a matrix whose every workspace failed before any model invocation."""

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from microcoder.config import Settings
from compute_bench.coding.runner import _recorded_results, execute_coding, resume_coding
from taskforge import TaskForge


class CodingRecoveryTests(unittest.TestCase):
    def test_results_jsonl_preserves_unicode_line_separator_inside_string(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = [{"run_id": "unicode-record", "case_id": "case-1"}]
            record = {**plan[0], "final_content": "before\u2028after"}
            (root / "results.jsonl").write_text(
                json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            results, recovered = _recorded_results(root, plan)

            self.assertEqual(results, [record])
            self.assertFalse(recovered)

    def test_duplicate_matrix_dimensions_are_rejected_before_bootstrap(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch("compute_bench.coding.runner.Sandbox") as sandbox:
            root = Path(temporary) / "must-not-exist"
            settings = Settings(api_key="synthetic-test-key")
            for conditions, defenses in ((["clean", "clean"], ["none"]), (["clean"], ["none", "none"])):
                with self.assertRaisesRegex(ValueError, "unique"):
                    execute_coding(settings, root, conditions=conditions, defenses=defenses)
            sandbox.assert_not_called()
            sandbox.probe.assert_not_called()
            self.assertFalse(root.exists())

    def test_pre_agent_failure_closes_receiver_and_resumes_the_same_assignment(self):
        def bootstrap(case, workspace, condition, variant):
            workspace.mkdir(parents=True)
            for relative, text in case["repo_files"].items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

        def fake_agent(agent, task, trace_path):
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text('{"kind":"synthetic-pre-agent-recovery"}\n')
            return {
                "status": "completed", "error": None, "final_content": "synthetic result",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "reasoning_tokens": 0},
                "llm_calls": 1, "tool_calls": 0, "latency_seconds": 0.1,
                "api_response_ids": ["synthetic"], "trace_file": str(trace_path),
            }

        with tempfile.TemporaryDirectory(prefix="cbr-") as temporary, \
             patch("compute_bench.coding.runner.Sandbox") as sandbox, \
             patch("compute_bench.coding.runner.create_workspace", side_effect=bootstrap), \
             patch("compute_bench.coding.runner.CodingEnvironment", side_effect=RuntimeError("synthetic pre-Agent failure")) as env, \
             patch("compute_bench.coding.runner.ChatClient") as client, \
             patch("compute_bench.coding.runner.CodingAgent.run", autospec=True, side_effect=fake_agent) as agent, \
             patch("compute_bench.coding.runner.grade_main", return_value={"passed": True}), \
             patch("compute_bench.coding.runner.scan_work", return_value=[]), \
             patch("builtins.print"):
            root = Path(temporary)
            settings = Settings(api_key="synthetic-test-key")
            sandbox.probe.return_value = {"backend": "synthetic", "available": True}
            sandbox.return_value.run.return_value = {"stdout": "synthetic patch", "stderr": "", "exit_code": 0}
            with self.assertRaisesRegex(RuntimeError, "failed in the harness"):
                execute_coding(settings, root, host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"], conditions=["clean"], repeats=1, workers=1)
            agent.assert_not_called()
            client.assert_not_called()
            assignment = TaskForge(root / "platform").status()["assignments"][0]
            self.assertEqual(assignment["state"], "interrupted")
            self.assertFalse((Path(assignment["workspace"]) / ".collector.sock").exists())
            registration_before = (root / "collector/registrations.jsonl").read_bytes()
            env.side_effect = lambda case, workspace, condition, **kwargs: SimpleNamespace(events=[], workspace=workspace)
            self.assertTrue(resume_coding(settings, root, workers=1)["all_planned_recorded"])
            self.assertEqual(agent.call_count, 1)
            recovered = TaskForge(root / "platform").status()["assignments"][0]
            self.assertEqual(recovered, {**assignment, "state": "closed"})
            self.assertEqual((root / "collector/registrations.jsonl").read_bytes(), registration_before)
            self.assertTrue((root / "recovery_1/failed_bootstrap/w000/solution.py").is_file())

    def test_all_bootstrap_failures_resume_without_lost_plan_or_fake_completed_runs(self):
        # Exercise both the new empty results journal and older failed runs
        # where no results journal was created. No model or sandbox runs here.
        for missing_journal in (False, True):
            with self.subTest(missing_journal=missing_journal), tempfile.TemporaryDirectory(prefix="coding-recover-") as temporary:
                root = Path(temporary) / "run"
                settings = Settings(api_key="synthetic-test-key", model="test-model")
                main_grade = {"passed": True, "public_passed": True, "hidden_passed": True}

                def fail_bootstrap(case, workspace, condition, variant):
                    workspace.mkdir(parents=True)
                    (workspace / "partial-bootstrap.txt").write_text("preserve this evidence")
                    raise OSError("synthetic bootstrap failure: Resource temporarily unavailable")

                def successful_bootstrap(case, workspace, condition, variant):
                    workspace.mkdir(parents=True)
                    for relative, text in case["repo_files"].items():
                        target = workspace / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(text)

                def environment(case, workspace, condition, **kwargs):
                    return SimpleNamespace(events=[], workspace=workspace)

                def fake_agent(session, user_task, trace_path):
                    trace_path.parent.mkdir(parents=True, exist_ok=True)
                    trace_path.write_text('{"kind":"synthetic-recovery-test"}\n')
                    return {
                        "status": "completed", "error": None, "final_content": "synthetic test result",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "reasoning_tokens": 0},
                        "llm_calls": 1, "tool_calls": 0, "latency_seconds": 0.1,
                        "api_response_ids": ["synthetic-" + trace_path.stem], "trace_file": str(trace_path),
                    }

                with patch("compute_bench.coding.runner.Sandbox") as sandbox, \
                     patch("compute_bench.coding.runner.create_workspace", side_effect=fail_bootstrap) as create, \
                     patch("compute_bench.coding.runner.ChatClient") as client, \
                     patch("compute_bench.coding.runner.CodingEnvironment", side_effect=environment), \
                     patch("compute_bench.coding.runner.CodingAgent.run", autospec=True, side_effect=fake_agent) as agent, \
                     patch("compute_bench.coding.runner.grade_main", return_value=main_grade), \
                     patch("compute_bench.coding.runner.scan_work", return_value=[]), \
                     patch("builtins.print"):
                    sandbox.probe.return_value = {"backend": "synthetic-test-sandbox", "available": True}
                    sandbox.return_value.run.return_value = {"stdout": "synthetic patch\n", "stderr": "", "exit_code": 0}
                    with self.assertRaisesRegex(RuntimeError, "failed in the harness") as raised:
                        execute_coding(settings, root, host_task_ids=["coding-01", "coding-02"], atomic_task_ids=["rewrite-user-record", "regression-empty-page"], conditions=["clean"],
                                       defenses=["none"], repeats=2, workers=1)
                    self.assertIn("synthetic bootstrap failure", str(raised.exception))
                    self.assertIn(str(root / "harness_errors.json"), str(raised.exception))

                    client.assert_not_called()
                    agent.assert_not_called()
                    plan = json.loads((root / "plan.json").read_text())
                    self.assertEqual(len(plan), 8)
                    self.assertEqual((root / "results.jsonl").read_text(), "")
                    failed_manifest = json.loads((root / "manifest.json").read_text())
                    self.assertEqual(failed_manifest["completed_runs"], 0)
                    self.assertEqual(failed_manifest["total_usage"]["total_tokens"], 0)
                    self.assertEqual(len(json.loads((root / "harness_errors.json").read_text())), 8)
                    self.assertFalse(json.loads((root / "summary.json").read_text())["all_planned_recorded"])
                    snapshot_before = (root / "source/compute_bench/coding/runner.py").read_bytes()
                    original_hashes = failed_manifest["source_sha256"]
                    platform_before = (root / "platform/plan.json").read_bytes()
                    self.assertEqual(TaskForge(root / "platform").status()["assignments"], [])

                    if missing_journal:
                        (root / "results.jsonl").unlink()
                    create.side_effect = successful_bootstrap
                    summary = resume_coding(settings, root, workers=1)

                    self.assertEqual(agent.call_count, 8)
                    self.assertEqual(client.call_count, 8)
                    self.assertTrue(summary["all_planned_recorded"])
                    self.assertEqual(summary["runs"], 8)
                    self.assertEqual(summary["total_usage"]["total_tokens"], 120)
                    records = [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines()]
                    self.assertEqual({item["run_id"] for item in records}, {item["run_id"] for item in plan})
                    self.assertEqual(len(records), len({item["run_id"] for item in records}))
                    self.assertTrue(all(item["execution_revision"] == "recovery_1" for item in records))
                    self.assertTrue(all(not item["valid_delivery"] for item in records))
                    self.assertEqual((root / "source/compute_bench/coding/runner.py").read_bytes(), snapshot_before)
                    recovered_manifest = json.loads((root / "manifest.json").read_text())
                    self.assertEqual(recovered_manifest["source_sha256"], original_hashes)
                    self.assertEqual(recovered_manifest["completed_runs"], 8)
                    recovery = json.loads((root / "recovery_1/recovery.json").read_text())
                    self.assertEqual(set(recovery["pending_run_ids"]), {item["run_id"] for item in plan})
                    self.assertEqual(recovery["failures"], [])
                    for trial in plan:
                        archived = root / "recovery_1/failed_bootstrap" / trial["workspace_id"] / "partial-bootstrap.txt"
                        self.assertEqual(archived.read_text(), "preserve this evidence")
                    registrations = (root / "collector/registrations.jsonl").read_text().splitlines()
                    self.assertEqual(len(registrations), 8)
                    self.assertEqual((root / "platform/plan.json").read_bytes(), platform_before)
                    platform = TaskForge(root / "platform")
                    assignments = platform.status()["assignments"]
                    self.assertEqual({item["assignment_id"] for item in assignments}, {item["run_id"] for item in plan})
                    self.assertTrue(all(item["state"] == "closed" for item in assignments))
                    self.assertEqual({item["routing_id"] for item in assignments}, {item["case_id"] for item in plan})
                    self.assertEqual(json.loads((root / "platform/result.json").read_text())["completed_tasks"], 0)
                    # Resuming a complete matrix must not mutate provenance or rerun a model.
                    manifest_before = (root / "manifest.json").read_bytes()
                    records_before = (root / "results.jsonl").read_bytes()
                    self.assertTrue(resume_coding(settings, root, workers=1)["all_planned_recorded"])
                    self.assertEqual(agent.call_count, 8)
                    self.assertEqual((root / "manifest.json").read_bytes(), manifest_before)
                    self.assertEqual((root / "results.jsonl").read_bytes(), records_before)
                    self.assertFalse((root / "recovery_2").exists())


if __name__ == "__main__":
    unittest.main()
