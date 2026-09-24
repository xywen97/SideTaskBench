"""Tamper tests for independent offline evidence verification.

The fixture uses a deterministic test double, clearly labeled with unit-fixture
response IDs. This is only a unit-test fixture; real experiment artifacts are
audited separately and are never overwritten by these tests.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.audit import audit_directory
from compute_bench.experiment import execute_experiment
from compute_bench.scenarios import build_cases


class FixtureClient:
    def __init__(self, settings):
        self.step = 0
        self.case = build_cases(1)[0]

    def complete(self, messages, tools):
        step = self.step
        self.step += 1
        actions = [
            ("search", {"query": self.case["query"]}),
            ("read_document", {"document_id": self.case["id"] + "-community-source"}),
            ("submit_result", self.case["crowd_gold"]),
        ]
        if step < len(actions):
            name, arguments = actions[step]
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"unit-call-{step}", "type": "function", "function": {
                    "name": name, "arguments": json.dumps(arguments),
                },
            }]}
        else:
            message = {"role": "assistant", "content": json.dumps(self.case["expected_answer"])}
        return message, {
            "response_id": f"unit-fixture-response-{step}",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
                      "completion_tokens_details": {"reasoning_tokens": 5}},
            "finish_reason": "tool_calls" if step < len(actions) else "stop",
        }

    def close(self):
        pass


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "experiment"
        settings = SimpleNamespace(public_metadata=lambda: {"model": "unit-test-fixture", "thinking": "default"})
        with patch("compute_bench.experiment.ChatClient", FixtureClient), redirect_stdout(io.StringIO()):
            execute_experiment(settings, self.directory, case_count=1, conditions=["wrapped"],
                               defenses=["none"], repeats=1, workers=1, label="unit-test-fixture")
        self.result = self.read_lines("results.jsonl")[0]
        self.run = self.result["run_id"]
        self.trace_path = f"traces/{self.run}.jsonl"

    def read(self, filename):
        return json.loads((self.directory / filename).read_text())

    def read_lines(self, filename):
        return [json.loads(line) for line in (self.directory / filename).read_text().splitlines() if line.strip()]

    def write(self, filename, value):
        (self.directory / filename).write_text(json.dumps(value))

    def write_lines(self, filename, records):
        (self.directory / filename).write_text("".join(json.dumps(record) + "\n" for record in records))

    def assert_failed_check(self, expected):
        report = audit_directory(self.directory)
        self.assertFalse(report["passed"], report)
        self.assertTrue(any(expected in error for error in report["errors"]), report["errors"])
        return report

    def test_valid_evidence_passes_without_network_or_environment_and_is_read_only(self):
        before = {path.relative_to(self.directory): path.read_bytes()
                  for path in self.directory.rglob("*") if path.is_file()}
        with patch("socket.socket", side_effect=AssertionError("Audit must never access the network")), patch.dict("os.environ", {}, clear=True):
            report = audit_directory(self.directory)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["independently_collected_work_units"], 6)
        self.assertEqual(report["independently_joint_successes"], 1)
        self.assertEqual(report["llm_responses"], 4)
        self.assertEqual(report["source_snapshot"], "verified")
        after = {path.relative_to(self.directory): path.read_bytes()
                 for path in self.directory.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_duplicate_run_and_plan_identity_tampering_fail(self):
        self.write_lines("results.jsonl", [self.result, deepcopy(self.result)])
        self.assert_failed_check("results_match_plan")
        changed = deepcopy(self.result)
        changed["repeat"] = 99
        self.write_lines("results.jsonl", [changed])
        self.assert_failed_check("run_matches_plan")

    def test_unreported_token_usage_and_missing_provider_id_fail(self):
        changed = deepcopy(self.result)
        changed["usage"]["total_tokens"] += 50
        self.write_lines("results.jsonl", [changed])
        report = self.assert_failed_check("run_usage_from_trace")
        self.assertTrue(any(self.run in error for error in report["errors"]))
        self.write_lines("results.jsonl", [self.result])
        trace = self.read_lines(self.trace_path)
        next(event for event in trace if event["kind"] == "llm")["metadata"]["response_id"] = None
        self.write_lines(self.trace_path, trace)
        self.assert_failed_check("llm_provider_evidence")

    def test_changed_final_answer_is_rescored_independently(self):
        trace = self.read_lines(self.trace_path)
        last = [event for event in trace if event["kind"] == "llm"][-1]
        last["message"]["content"] = "I completed the task."
        self.write_lines(self.trace_path, trace)
        self.assert_failed_check("legitimate_rescored")

    def test_model_arguments_must_match_recorded_tool_execution(self):
        trace = self.read_lines(self.trace_path)
        tool = next(event for event in trace if event.get("name") == "submit_result")
        tool["arguments"]["rows"][0]["priority"] = "forged-priority"
        self.write_lines(self.trace_path, trace)
        self.assert_failed_check("tool_matches_model_call")

    def test_server_receipt_cannot_replace_actual_model_work(self):
        receipts = self.read_lines("collector/receipts.jsonl")
        receipts[0]["submitted_rows"][0]["category"] = "forged-category"
        self.write_lines("collector/receipts.jsonl", receipts)
        self.assert_failed_check("receipt_independent_validation")

    def test_delivery_requires_server_persistence(self):
        (self.directory / "collector" / "receipts.jsonl").unlink()
        self.assert_failed_check("all_delivery_returns_persisted")

    def test_aggregate_cannot_invent_or_duplicate_delivered_rows(self):
        batch = self.read("collected_batch.json")
        batch["task_results"][0]["rows"].append(deepcopy(batch["task_results"][0]["rows"][0]))
        batch["effective_work_units"] += 1
        self.write("collected_batch.json", batch)
        self.assert_failed_check("collected_batch_from_delivered_rows")

    def test_false_success_flags_are_recomputed(self):
        changed = deepcopy(self.result)
        changed["joint_success"] = False
        changed["correct_work_observed"] = False
        self.write_lines("results.jsonl", [changed])
        self.assert_failed_check("run_metrics_independent")

    def test_source_hashes_detect_modification_but_legacy_absence_is_reported(self):
        source = self.directory / "source" / "compute_bench" / "scoring.py"
        source.write_text(source.read_text() + "\n# unexpected modification\n")
        self.assert_failed_check("source_snapshot_hashes")
        shutil.rmtree(self.directory / "source")
        report = audit_directory(self.directory)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["source_snapshot"], "unavailable")
        self.assertTrue(report["warnings"])

    def test_malformed_or_missing_artifacts_return_failure_instead_of_crashing(self):
        (self.directory / "cases.json").write_text("{broken-json")
        self.assert_failed_check("artifact_readable")
        report = audit_directory(self.directory / "nonexistent")
        self.assertFalse(report["passed"])
        self.assertTrue(report["errors"])


if __name__ == "__main__":
    unittest.main()
