"""Corrected evidence must retain original trajectories and source provenance."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.audit import audit_corrected, audit_directory
from compute_bench.coding.grading import ADDITIONAL_TOPOLOGICAL_TESTS
from compute_bench.coding.tasks import build_coding_cases
from test_coding_audit import _fixture, _grade, _lines, _sha, _write


def _sidecars(root, corrected):
    original = json.loads((root / "results.jsonl").read_text().splitlines()[0])
    corrected = deepcopy(corrected)
    corrected["evaluation_version"] = "coding_acceptance_v2"
    _lines(root / "corrected_results.jsonl", [corrected])
    source = root / "evaluation_source"
    source.mkdir(exist_ok=True)
    grading = Path(__file__).resolve().parents[1] / "compute_bench/coding/grading.py"
    (source / "grading.py").write_bytes(grading.read_bytes())
    changes = {key: {"original": original[key], "corrected": corrected[key]} for key in
               ("correct_work_observed", "valid_delivery", "strict_success", "joint_success") if original[key] != corrected[key]}
    if original["legitimate"]["passed"] != corrected["legitimate"]["passed"]:
        changes["main_pass"] = {"original": original["legitimate"]["passed"], "corrected": corrected["legitimate"]["passed"]}
    case = build_coding_cases(1)[0]
    task = case["crowd_task"]
    receipt = next((item for item in corrected["receipts"] if item["valid"]), None)
    library = root / "verified_library"
    library.mkdir(exist_ok=True)
    item = {"task_id": task["task_id"], "function_name": task["function_name"], "complete": receipt is not None}
    if receipt:
        for key in ("receipt_id", "run_id", "source_sha256"):
            item[key] = receipt[key]
        item["source_file"] = str(library / "merge_intervals.py")
        (library / "merge_intervals.py").write_text(receipt["source_code"])
    (library / "__init__.py").write_text("from .merge_intervals import merge_intervals\n" if receipt else "\n")
    correction = {"evaluation_version": "coding_acceptance_v2", "grader_sha256": hashlib.sha256(grading.read_bytes()).hexdigest(),
                  "original_results_sha256": hashlib.sha256((root / "results.jsonl").read_bytes()).hexdigest(),
                  "corrected_results_sha256": hashlib.sha256((root / "corrected_results.jsonl").read_bytes()).hexdigest(),
                  "additional_tests": ADDITIONAL_TOPOLOGICAL_TESTS, "regraded_with_llm": False,
                  "runs_regraded": 1, "total_functions": 1, "completed_functions": int(receipt is not None),
                  "complete_library": receipt is not None, "task_results": [item],
                  "changes": [{"run_id": corrected["run_id"], "differences": changes}] if changes else []}
    _write(root / "evaluation_corrections.json", correction)


class CorrectedAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="coding-corrected-audit-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_corrected_audit_preserves_compact_layout_provenance_requirements(self):
        original, _ = _fixture(self.root)
        _sidecars(self.root, original)
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(manifest["source_layout_version"], 4)
        self.assertNotIn("agent.py", manifest["source_sha256"])
        audited = audit_corrected(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        (self.root / "source/compute_bench/coding/platform.py").unlink()
        manifest["source_sha256"].pop("coding/platform.py")
        _write(self.root / "manifest.json", manifest)
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("source_snapshot_present" in error for error in audited["errors"]))

    def test_corrected_sidecar_cannot_change_trajectory_or_received_source(self):
        original, _ = _fixture(self.root)
        _sidecars(self.root, original)
        audited = audit_corrected(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        edited = deepcopy(original)
        edited["final_content"] = "Tampered assistant response"
        _sidecars(self.root, edited)
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("immutable_trajectory" in error for error in audited["errors"]))
        edited = deepcopy(original)
        edited["receipts"][0]["source_code"] += "\n# code never received\n"
        _sidecars(self.root, edited)
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("immutable_submission" in error for error in audited["errors"]))

    def test_deleted_candidate_requires_exact_successful_raw_write_event(self):
        original, trace = _fixture(self.root, delivered=False)
        case = build_coding_cases(1)[0]
        source = case["crowd_reference_code"]
        event = {"tool": "write_file", "args": {"path": "/workspace/reference_work/merge_intervals.py", "content": source},
                 "result": {"written": "reference_work/merge_intervals.py", "bytes": len(source.encode()), "sha256": _sha(source)},
                 "exposed": False}
        original["events"].append(event)
        original["tool_calls"] += 1
        trace[1]["message"]["tool_calls"].append({"id": "fixture-call-2", "function": {"name": "write_file", "arguments": json.dumps(event["args"])}})
        trace.insert(3, {"kind": "tool", "step": 0, "name": "write_file", "arguments": event["args"], "result": event["result"]})
        trace[-1]["result"]["tool_calls"] += 1
        _lines(self.root / "results.jsonl", [original])
        _write(self.root / "results" / (original["run_id"] + ".json"), original)
        _lines(self.root / "traces" / (original["run_id"] + ".jsonl"), trace)
        corrected = deepcopy(original)
        corrected["observed_work"] = [{"path": "reference_work/merge_intervals.py", "source_code": source,
                                      "source_sha256": _sha(source), "grade": _grade(source, case["crowd_tests"]),
                                      "provenance": "trace_write_file", "event_index": 1}]
        corrected["correct_work_observed"] = True
        _sidecars(self.root, corrected)
        self.assertFalse((self.root / "workspaces/w000/reference_work/merge_intervals.py").exists())
        audited = audit_corrected(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        self.assertEqual(audited["statistics"]["correct_work_runs"], 1)
        self.assertEqual(audited["statistics"]["valid_deliveries"], 0)
        falsely_rejected = deepcopy(corrected)
        falsely_rejected["observed_work"][0]["grade"] = {"passed": False, "tests_run": 0,
            "source_sha256": _sha(source), "policy_errors": ["synthetic false rejection"]}
        falsely_rejected["correct_work_observed"] = False
        _sidecars(self.root, falsely_rejected)
        with patch("compute_bench.coding.audit.grade_main", return_value=original["legitimate"]), \
             patch("compute_bench.coding.audit.grade_crowd", return_value=_grade(source, case["crowd_tests"])) as regrade:
            audited = audit_corrected(self.root, regrade=True)
        self.assertEqual(regrade.call_count, 1, "Negative corrected verdicts must also be independently executed")
        self.assertFalse(audited["passed"])
        self.assertTrue(any("/current_regrade" in error for error in audited["errors"]))
        corrected["observed_work"][0]["source_code"] += "\n# never written by the Agent\n"
        _sidecars(self.root, corrected)
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("/provenance" in error for error in audited["errors"]))
        # Future raw runs may persist the same deleted-source evidence directly.
        original["observed_work"] = [{"path": "reference_work/merge_intervals.py", "source_code": source,
                                     "source_sha256": _sha(source), "grade": _grade(source, case["crowd_tests"]),
                                     "provenance": "trace_write_file", "event_index": 1}]
        original["correct_work_observed"] = True
        _lines(self.root / "results.jsonl", [original])
        _write(self.root / "results" / (original["run_id"] + ".json"), original)
        raw_audited = audit_directory(self.root)
        self.assertTrue(raw_audited["passed"], raw_audited["errors"])
        original["observed_work"][0]["event_index"] = 0
        _lines(self.root / "results.jsonl", [original])
        _write(self.root / "results" / (original["run_id"] + ".json"), original)
        raw_audited = audit_directory(self.root)
        self.assertFalse(raw_audited["passed"])
        self.assertTrue(any("_write_event" in error for error in raw_audited["errors"]))


if __name__ == "__main__":
    unittest.main()
