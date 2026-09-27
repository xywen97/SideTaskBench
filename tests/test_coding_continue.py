"""Repeated run commands preserve old trials and execute only missing work."""

from dataclasses import replace
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.audit import audit_directory
from compute_bench.coding.runner import execute_coding, _run_lock
from microcoder.config import Settings
from microcoder.sandbox import Sandbox
from test_coding_audit import _fixture


class CodingContinueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cb-continue-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"

    def test_long_output_supports_sandbox_delivery_and_resume(self):
        self.root = self.root / ("long-output-" * 12)

        def deliver(agent):
            payload = json.dumps({"task_id": agent.tools.case["crowd_task"]["task_id"],
                                  "artifact": agent.tools.case["crowd_reference_artifact"]})
            result = Sandbox(agent.tools.workspace).run(
                "curl --silent --show-error --unix-socket /workspace/.collector.sock "
                "-H 'Content-Type: application/json' --data " + shlex.quote(payload)
                + " http://collector/submit")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertTrue(json.loads(result["stdout"])["valid"])

        # Leave a prepared trial with no LLM trajectory, then repeat the same
        # command to exercise automatic recovery at the original long path.
        with patch("compute_bench.coding.runner.CodingEnvironment", side_effect=RuntimeError("before LLM")), \
             self.assertRaisesRegex(RuntimeError, "before LLM"):
            _fixture(self.root, atomic_task_ids=["regression-empty-page"])
        result, _ = _fixture(self.root, atomic_task_ids=["regression-empty-page"],
                             inspect_agent=deliver)
        self.assertTrue(result["valid_delivery"])
        self.assertEqual(result["execution_revision"], "recovery_1")
        manifest = json.loads((self.root / "manifest.json").read_text())
        registrations = [json.loads(line) for line in
                         (self.root / "collector/registrations.jsonl").read_text().splitlines()]
        path = self.root / "workspaces/w000/.collector.sock"
        self.assertEqual([item["socket_path"] for item in registrations], [str(path)])
        self.assertFalse(path.exists())
        audit = audit_directory(self.root)
        self.assertTrue(audit["passed"], audit["errors"])

    def test_expanding_hosts_and_repeats_preserves_old_results_and_passes_audit(self):
        _fixture(self.root)
        original_plan = json.loads((self.root / "plan.json").read_text())
        original_results = (self.root / "results.jsonl").read_bytes()
        original_result = (self.root / "results" / (original_plan[0]["run_id"] + ".json")).read_bytes()
        original_solution = (self.root / "workspaces/w000/solution.py").read_bytes()
        calls = []
        _fixture(self.root, host_task_ids=["coding-01", "coding-02"], repeats=2,
                 inspect_agent=lambda agent: calls.append(agent.tools.case["id"]))
        self.assertEqual(len(calls), 3)
        plan = json.loads((self.root / "plan.json").read_text())
        self.assertEqual(plan[:1], original_plan)
        self.assertEqual(len(plan), 4)
        self.assertEqual(len({item["workspace_id"] for item in plan}), 4)
        self.assertTrue((self.root / "results.jsonl").read_bytes().startswith(original_results))
        self.assertEqual((self.root / "results" / (original_plan[0]["run_id"] + ".json")).read_bytes(), original_result)
        self.assertEqual((self.root / "workspaces/w000/solution.py").read_bytes(), original_solution)
        self.assertEqual(json.loads((self.root / "extension_1/plan.json").read_text()), original_plan)
        audit = audit_directory(self.root)
        self.assertTrue(audit["passed"], audit["errors"])
        # A second expansion must preserve all previously allocated workspace IDs as well.
        _fixture(self.root, host_task_ids=["coding-01", "coding-02"], repeats=3)
        self.assertEqual(json.loads((self.root / "plan.json").read_text())[:4], plan)
        audit = audit_directory(self.root)
        self.assertTrue(audit["passed"], audit["errors"])
        saved = {name: (self.root / name).read_bytes() for name in ("manifest.json", "results.jsonl", "plan.json")}
        _fixture(self.root, host_task_ids=["coding-01", "coding-02"], repeats=3,
                 inspect_agent=lambda agent: self.fail("Completed run was executed again"))
        self.assertEqual(saved, {name: (self.root / name).read_bytes() for name in saved})

    def test_started_incomplete_does_not_block_unstarted_trials(self):
        calls = []

        def interrupt(agent):
            calls.append(agent.tools.case["id"])
            if len(calls) > 1:
                raise OSError("synthetic pre-trajectory failure")

        with self.assertRaisesRegex(RuntimeError, "failed in the harness"):
            _fixture(self.root, repeats=3, inspect_agent=interrupt)
        records = (self.root / "results.jsonl").read_bytes()
        done = json.loads(records)["run_id"]
        pending = [trial for trial in json.loads((self.root / "plan.json").read_text()) if trial["run_id"] != done]
        trace = self.root / "traces" / (pending[0]["run_id"] + ".jsonl")
        trace.write_text('{"kind":"interrupted-model-call"}\n')
        seen = []
        _fixture(self.root, repeats=3, inspect_agent=lambda agent: seen.append(agent.tools.case["id"]))
        self.assertEqual(len(seen), 1)
        self.assertEqual(trace.read_text(), '{"kind":"interrupted-model-call"}\n')
        self.assertTrue((self.root / "results.jsonl").read_bytes().startswith(records))
        recovery = json.loads((self.root / "recovery_1/recovery.json").read_text())
        self.assertEqual(recovery["skipped_started_incomplete"], [pending[0]["run_id"]])
        summary = json.loads((self.root / "summary.json").read_text())
        self.assertEqual(summary["runs"], 2)
        self.assertFalse(summary["all_planned_recorded"])

    def test_complete_result_missing_from_journal_is_recovered_without_model_call(self):
        _fixture(self.root)
        result = json.loads((self.root / "results.jsonl").read_text())
        (self.root / "results.jsonl").write_text("")
        _fixture(self.root, inspect_agent=lambda agent: self.fail("Persisted result was rerun"))
        self.assertEqual(json.loads((self.root / "results.jsonl").read_text()), result)
        audit = audit_directory(self.root)
        self.assertTrue(audit["passed"], audit["errors"])

    def test_changed_experiment_settings_and_shrinking_selection_are_rejected(self):
        _fixture(self.root, repeats=2)
        saved = {name: (self.root / name).read_bytes() for name in ("manifest.json", "results.jsonl", "plan.json")}
        settings = Settings(api_key="fixture", model="fixture-model")
        arguments = dict(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"], repeats=2)
        for changes in ({"max_steps": 99}, {"variant": "companion_v1"}, {"seed": 1}, {"repeats": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                execute_coding(settings, self.root, **{**arguments, **changes})
        with self.assertRaisesRegex(ValueError, "model/settings"):
            execute_coding(replace(settings, model="other-model"), self.root, **arguments)
        self.assertEqual(saved, {name: (self.root / name).read_bytes() for name in saved})
        with _run_lock(self.root), self.assertRaisesRegex(ValueError, "active benchmark"):
            execute_coding(settings, self.root, **arguments)

if __name__ == "__main__":
    unittest.main()
