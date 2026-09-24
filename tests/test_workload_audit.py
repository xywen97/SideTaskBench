"""Offline audit adversarial checks with a fake provider and real local HTTP."""

import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.workloads.audit import _Audit, audit_directory
from compute_bench.workloads.registry import load_case
from compute_bench.workloads.runner import execute_workloads
from microcoder.config import Settings


def _read(path):
    return json.loads(path.read_text())


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_lines(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


class WorkloadAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="wl-audit-")
        cls.base = Path(cls.temporary.name)
        case = load_case("order-reconciliation")
        task = case.tasks[0]
        good = {"task_id": task["task_id"], "artifact": case.reference_artifacts[task["task_id"]]}
        bad = {"task_id": task["task_id"], "artifact": {"kind": "json", "value": {}}}

        def submit_command(payloads, projected):
            return ("python3 - <<'PY'\nimport json, subprocess\n"
                    + "payloads = " + repr(payloads) + "\n"
                    + "for i, payload in enumerate(payloads):\n"
                    + "    result = subprocess.run(['curl', '-sS', '--unix-socket', '/workspace/.collector.sock', "
                    "'-H', 'Content-Type: application/json', '--data-binary', '@-', 'http://collector/submit'], "
                    "input=json.dumps(payload), capture_output=True, text=True, check=True)\n"
                    + ("    print(i, 'valid=', json.loads(result.stdout)['valid'])\n" if projected else
                       "    print(result.stdout.strip())\n") + "PY")

        commands = [submit_command([{}, bad, good], False), submit_command([good, good], True)]

        class ExplicitFakeProvider:
            def __init__(self, settings):
                self.calls = 0

            def complete(self, messages, tools):
                self.calls += 1
                metadata = {"response_id": "audit-fixture-not-real-provider-" + str(self.calls),
                            "usage": {"total_tokens": 0}}
                if self.calls == 1:
                    return {"role": "assistant", "content": "", "tool_calls": [
                        {"id": "fixture-submit-" + str(index), "type": "function", "function": {
                            "name": "shell", "arguments": json.dumps({"command": command})}}
                        for index, command in enumerate(commands)]}, metadata
                return {"role": "assistant", "content": "Explicit offline fixture; no model was called."}, metadata

            def close(self):
                pass

        for mode in ("authorized", "injected"):
            with patch("compute_bench.workloads.runner.ChatClient", ExplicitFakeProvider), contextlib.redirect_stdout(io.StringIO()):
                execute_workloads(Settings(api_key="fixture-no-api"), cls.base / mode,
                                  case_ids=[case.case_id], mode=mode, conditions=["wrapped"],
                                  selection="first", workers=1)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.copy = tempfile.TemporaryDirectory(prefix="wl-audit-copy-")
        self.root = Path(self.copy.name) / "run"
        shutil.copytree(self.base / "authorized", self.root)
        self.job = self.root / "jobs/order-reconciliation-authorized"

    def tearDown(self):
        self.copy.cleanup()

    def assert_failed(self, report, prefix):
        self.assertFalse(report["passed"])
        self.assertTrue(any(error.startswith(prefix) for error in report["errors"]), report["errors"])

    def guarded_regrade(self):
        def no_execution(*args, **kwargs):
            raise AssertionError("Untrusted evidence must not reach candidate evaluation")

        def guarded_case(*args, **kwargs):
            return replace(load_case(*args, **kwargs), grade_task=no_execution, assemble=no_execution,
                           grade_final=no_execution)

        with patch("compute_bench.workloads.audit.load_case", side_effect=guarded_case), patch(
                "compute_bench.coding.grading.grade_main", side_effect=no_execution):
            result = audit_directory(self.root, regrade=True)
        self.assertEqual(result["regraded_receipts"], 0)
        self.assertEqual(result["regraded_jobs"], 0)
        self.assertEqual(result["regraded_main_tasks"], 0)
        return result

    def test_valid_audit_is_read_only_and_keeps_every_receipt(self):
        def inventory():
            return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob("*") if p.is_file()}

        before = inventory()
        result = audit_directory(self.root)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["receipts"], 5)
        self.assertEqual(result["http_receipts_with_id"], 3)
        self.assertEqual(result["http_receipts_with_projected_verdict"], 2)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(inventory(), before)

    def test_regrades_invalid_protocol_invalid_work_and_duplicates(self):
        result = audit_directory(self.root, regrade=True)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["regraded_receipts"], 5)
        self.assertEqual(result["regraded_protocol_rejections"], 1)
        self.assertEqual(result["regraded_jobs"], 1)

    def test_injected_main_task_is_regraded(self):
        result = audit_directory(self.base / "injected", regrade=True)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["regraded_main_tasks"], 1)

    def test_injected_main_candidate_change_blocks_all_evaluation(self):
        shutil.rmtree(self.root)
        shutil.copytree(self.base / "injected", self.root)
        candidate = self.root / "w/j00-t00/solution.py"
        candidate.write_text(candidate.read_text() + "\n# changed after grading\n")
        self.assert_failed(self.guarded_regrade(), "main_candidate_hash/")

    def test_main_case_mapping_cannot_be_reassigned(self):
        path = self.root / "manifest.json"
        manifest = _read(path)
        manifest["jobs"][0]["main_case_index"] = 0
        _write(path, manifest)
        self.assert_failed(self.guarded_regrade(), "main_case_mapping/")

    def test_summary_change_blocks_all_regrading(self):
        path = self.root / "summary.json"
        summary = _read(path)
        summary["valid_deliveries"] += 1
        _write(path, summary)
        self.assert_failed(self.guarded_regrade(), "summary_counts")

    def test_trace_change_even_with_refreshed_hash_blocks_regrading(self):
        trace = self.root / "traces/j00-t00.jsonl"
        events = _lines(trace)
        tool = next(e for e in events if e.get("kind") == "tool")
        tool["arguments"]["command"] += "\n# tool arguments were changed after the model call\n"
        _write_lines(trace, events)
        attempt_path = self.root / "attempts/j00-t00.json"
        attempt = _read(attempt_path)
        attempt["trace_sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
        _write(attempt_path, attempt)
        self.assert_failed(self.guarded_regrade(), "trace_tool_arguments/")

    def test_projected_verdict_cannot_disagree_with_journal(self):
        trace = self.root / "traces/j00-t00.jsonl"
        events = _lines(trace)
        event = next(e for e in events if e.get("kind") == "tool" and "0 valid=" in e["result"].get("stdout", ""))
        event["result"]["stdout"] = event["result"]["stdout"].replace("0 valid= True", "0 valid= False")
        _write_lines(trace, events)
        attempt_path = self.root / "attempts/j00-t00.json"
        attempt = _read(attempt_path)
        attempt["trace_sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
        _write(attempt_path, attempt)
        self.assert_failed(self.guarded_regrade(), "receipt_http_trace/")

    def test_pregrade_journal_cannot_silently_drop_invalid_submission(self):
        path = self.job / "collector/received.jsonl"
        _write_lines(path, _lines(path)[1:])
        self.assert_failed(self.guarded_regrade(), "receipt_pregrade_journal/")

    def test_ungraded_journal_entry_is_not_silently_ignored(self):
        path = self.job / "collector/received.jsonl"
        rows = _lines(path)
        rows.append({**rows[0], "receipt_id": "orphan-receipt"})
        _write_lines(path, rows)
        self.assert_failed(self.guarded_regrade(), "journal_inventory/")

    def test_final_artifact_mutation_blocks_regrading(self):
        path = self.job / "result/artifacts/artifact.json"
        artifact = _read(path)
        artifact["injected_after_run"] = True
        _write(path, artifact)
        self.assert_failed(self.guarded_regrade(), "aggregate_artifact/")

    def test_assignment_cannot_rebind_task(self):
        path = self.job / "assignments/j00-t00.json"
        assignment = _read(path)
        assignment["routing_id"] = "unrelated-task"
        _write(path, assignment)
        self.assert_failed(self.guarded_regrade(), "assignment_binding/")

    def test_missing_declared_snapshot_file_blocks_evaluation(self):
        (self.root / "source/compute_bench/workloads/evaluation.py").unlink()
        with patch("compute_bench.workloads.audit.load_case") as evaluator:
            result = audit_directory(self.root, regrade=True)
        evaluator.assert_not_called()
        self.assert_failed(result, "source_inventory/compute_bench")

    def test_self_consistent_changed_snapshot_cannot_be_executed(self):
        path = self.root / "source/compute_bench/workloads/evaluation.py"
        path.write_text(path.read_text() + "\nraise RuntimeError('untrusted snapshot')\n")
        manifest_path = self.root / "manifest.json"
        manifest = _read(manifest_path)
        manifest["source_sha256"]["workloads/evaluation.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
        _write(manifest_path, manifest)
        with patch("compute_bench.workloads.audit.load_case") as evaluator:
            result = audit_directory(self.root, regrade=True)
        evaluator.assert_not_called()
        self.assert_failed(result, "current_evaluator_source/compute_bench/workloads/evaluation.py")

    def test_regression_only_evaluator_gate_includes_shared_helpers(self):
        manifest = _read(self.root / "manifest.json")
        manifest["case_ids"] = ["regression-tests"]
        manifest["source_sha256"]["workloads/evaluators/api_migration.py"] = "0" * 64
        audit = _Audit(self.root, regrade=True)
        self.assertFalse(audit.evaluator_matches(manifest))
        self.assertIn("current_evaluator_source/compute_bench/workloads/evaluators/api_migration.py", audit.errors)

    def test_new_run_snapshots_definition_and_material_bytes(self):
        manifest = _read(self.root / "manifest.json")
        self.assertEqual(manifest["workload_definition_version"], 1)
        from compute_bench.workloads.registry import CASE_MODULES
        self.assertEqual(manifest["workload_resource_case_ids"], list(CASE_MODULES))
        resources = manifest["workload_resource_sha256"]
        self.assertIn("order_reconciliation/task.json", resources)
        self.assertIn("order_reconciliation/materials/README.md", resources)
        self.assertIn("api_migration/task.json", resources)  # unselected catalogue dependency
        for name, expected in resources.items():
            content = (self.root / "workload_resources" / name).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), expected)

    def test_definition_snapshot_tamper_blocks_candidate_execution(self):
        path = self.root / "workload_resources/order_reconciliation/task.json"
        definition = _read(path)
        definition["title"] += " changed"
        _write(path, definition)
        self.assert_failed(self.guarded_regrade(), "workload_resource_hash/")

    def test_material_rehash_cannot_break_recorded_public_spec(self):
        relative = "order_reconciliation/materials/README.md"
        path = self.root / "workload_resources" / relative
        path.write_text("Replaced public material\n")
        manifest_path = self.root / "manifest.json"
        manifest = _read(manifest_path)
        manifest["workload_resource_sha256"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        _write(manifest_path, manifest)
        self.assert_failed(self.guarded_regrade(), "workload_static_material/")

    def test_resource_binding_preserves_crlf_document_bytes(self):
        relative = "order_reconciliation/materials/README.md"
        path = self.root / "workload_resources" / relative
        content = path.read_bytes().replace(b"\n", b"\r\n")
        path.write_bytes(content)
        manifest = _read(self.root / "manifest.json")
        manifest["workload_resource_sha256"][relative] = hashlib.sha256(content).hexdigest()
        public_path = self.root / "cases/order-reconciliation.json"
        public = _read(public_path)
        public["public_files"]["README.md"] = content.decode("utf-8")
        _write(public_path, public)
        audit = _Audit(self.root, regrade=False)
        audit.resources(manifest)
        self.assertFalse(audit.errors, audit.errors)

    def test_extra_resource_is_not_silently_ignored(self):
        (self.root / "workload_resources/unrecorded.txt").write_text("not declared")
        self.assert_failed(self.guarded_regrade(), "workload_resource_inventory")

    def test_resource_symlink_is_rejected_without_reading_external_file(self):
        path = self.root / "workload_resources/order_reconciliation/materials/README.md"
        path.unlink()
        outside = Path(self.copy.name) / "external.txt"
        outside.write_text("external resource")
        path.symlink_to(outside)
        self.assert_failed(self.guarded_regrade(), "workload_resource_regular/")

    def test_unselected_definition_tamper_is_detected(self):
        path = self.root / "workload_resources/api_migration/task.json"
        definition = _read(path)
        definition["case_number"] = 100
        _write(path, definition)
        self.assert_failed(self.guarded_regrade(), "workload_resource_hash/")

    def test_current_resource_changes_fail_the_regrade_gate(self):
        with patch("compute_bench.workloads.audit.current_resource_hashes", return_value={}), patch(
                "compute_bench.workloads.audit.load_case") as evaluator:
            result = audit_directory(self.root, regrade=True)
        evaluator.assert_not_called()
        self.assert_failed(result, "current_workload_resources")

    def test_unknown_definition_version_is_rejected(self):
        path = self.root / "manifest.json"
        manifest = _read(path)
        manifest["workload_definition_version"] = 999
        _write(path, manifest)
        self.assert_failed(self.guarded_regrade(), "workload_definition_version")

    def test_seed_change_detected_against_public_spec(self):
        path = self.root / "manifest.json"
        manifest = _read(path)
        manifest["seed"] += 1
        _write(path, manifest)
        self.assert_failed(self.guarded_regrade(), "public_spec_seed/")

    def test_relative_path_escape_rejected(self):
        path = self.root / "manifest.json"
        manifest = _read(path)
        manifest["jobs"][0]["directory"] = "../untrusted"
        _write(path, manifest)
        self.assert_failed(self.guarded_regrade(), "artifact_readable_and_well_formed")


if __name__ == "__main__":
    unittest.main()
