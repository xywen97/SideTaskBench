"""Tamper tests for offline coding evidence; fixtures are explicitly synthetic."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.audit import audit_directory
from compute_bench.coding.documents import render_reference
from compute_bench.coding.environment import TOOLS
from microcoder.prompts import SYSTEM, BOUNDARY
from microcoder.sandbox import BACKEND
from compute_bench.coding.tasks import build_coding_cases
from compute_bench.coding.provenance import snapshot_sources, inspect_agent_snapshot, inspect_platform_snapshot


def _sha(source):
    return hashlib.sha256(source.encode()).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _lines(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values))


def _grade(source, tests):
    count = sum(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in ast.walk(ast.parse(tests)))
    verdict = {"ran": count, "failures": 0, "errors": 0, "skipped": 0, "successful": True}
    return {"passed": True, "tests_run": count, "expected_tests": count, "source_sha256": _sha(source),
            "verdict": verdict, "execution": {"stdout": "__BENCH_GRADE__=" + json.dumps(verdict) + "\n",
            "stderr": "synthetic fixture, not an execution log", "exit_code": 0, "timed_out": False, "sandbox": BACKEND}}


def _fixture(root, defense="none", delivered=True):
    """Produce internally consistent unit-test data, never benchmark evidence."""
    case = build_coding_cases(1)[0]
    task = case["crowd_task"]
    trial = {"run_id": f"coding-01__wrapped__{defense}__r1", "case_id": case["id"],
             "condition": "wrapped", "defense": defense, "repeat": 1, "workspace_id": "w000"}
    run_id = trial["run_id"]
    workspace = root / "workspaces/w000"
    workspace.mkdir(parents=True)
    for relative, source in case["repo_files"].items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    fixed = case["reference_files"]["solution.py"]
    (workspace / "solution.py").write_text(fixed)
    main = {"passed": True, "public_passed": True, "hidden_passed": True,
            "public": _grade(fixed, case["repo_files"]["tests/test_solution.py"]),
            "hidden": _grade(fixed, case["hidden_tests"]), "candidate_sha256": _sha(fixed), "changed": True}
    receipts, observed = [], []
    if delivered:
        source = case["crowd_reference_code"]
        crowd_grade = _grade(source, case["crowd_tests"])
        candidate = workspace / "reference_work/merge_intervals.py"
        candidate.parent.mkdir()
        candidate.write_text(source)
        observed = [{"path": "reference_work/merge_intervals.py", "source_sha256": _sha(source),
                     "source_code": source, "grade": crowd_grade}]
        receipts = [{"receipt_id": "fixture-receipt-1", "received_at": 1, "run_id": run_id,
                     "case_id": case["id"], "task_id": task["task_id"], "source_code": source,
                     "source_sha256": _sha(source), "valid": True, "blocked": False,
                     "grade": crowd_grade, "transport": "HTTP over workspace Unix socket"}]
    output = json.dumps({"receipt_id": "fixture-receipt-1", "accepted": True, "valid": True, "task_id": task["task_id"]}) if delivered else ""
    event = {"tool": "shell", "args": {"command": "python3 -m unittest discover -s tests -v"},
             "result": {"stdout": output, "stderr": "", "exit_code": 0, "timed_out": False, "sandbox": BACKEND},
             "exposed": False}
    usage = {"prompt_tokens": 20, "completion_tokens": 6, "total_tokens": 26, "reasoning_tokens": 0,
             "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 0}
    outcome = {"status": "completed", "error": None, "final_content": "Unit-test fixture only.", "usage": usage,
               "llm_calls": 2, "provider_truncated": False, "latency_seconds": 0, "tool_calls": 1,
               "api_response_ids": ["fixture-response-1", "fixture-response-2"],
               "trace_file": str(root / "traces" / (run_id + ".jsonl"))}
    result = {**trial, **outcome, "legitimate": main, "exposed": False,
              "submission_attempted": delivered, "correct_work_observed": delivered,
              "valid_delivery": delivered, "strict_success": delivered, "joint_success": delivered,
              "observed_work": observed, "receipts": receipts, "events": [event],
              "crowd_task_id": task["task_id"], "function_name": task["function_name"],
              "workspace": str(workspace), "patch_file": str(root / "patches" / (run_id + ".diff"))}
    manifest = {"schema_version": 2, "track": "coding", "label": "unit-test synthetic fixture",
                "finished_at": "fixture", "settings": {"model": "fixture-model", "max_tokens_parameter": "omitted",
                "token_budget": None, "thinking": "default"}, "case_count": 1, "conditions": ["wrapped"],
                "defenses": [defense], "repeats": 1, "seed": 1, "planned_runs": 1, "completed_runs": 1,
                "max_steps": 45, "variant": "companion_v1", "system_prompt": SYSTEM, "boundary_prompt": BOUNDARY,
                "tools": TOOLS, "output_token_limit": None,
                "sandbox": {"backend": BACKEND, "available": True, "unsandboxed_fallback": False,
                "landlock_abi": 4, **{key: True for key in ("mount_namespace", "network_namespace", "ipc_namespace",
                "pid_namespace", "chroot", "seccomp", "no_new_privileges")}},
                "total_usage": {key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens")}}
    manifest.update(snapshot_sources(root))
    messages = [{"role": "system", "content": SYSTEM + (BOUNDARY if defense == "boundary" else "")},
                {"role": "user", "content": case["user_task"]}]
    request = {"model": "fixture-model", "messages": messages, "tools": TOOLS, "tool_choice": "auto"}
    llm_metadata = {"response_id": "fixture-response-1", "request_sha256": _sha(json.dumps(request, ensure_ascii=False, sort_keys=True)),
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}}
    trace = [
        {"kind": "start", "messages": messages, "max_steps": 45},
        {"kind": "llm", "step": 0, "message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "fixture-call-1", "function": {"name": "shell", "arguments": json.dumps(event["args"])}}]},
         "metadata": llm_metadata},
        {"kind": "tool", "step": 0, "name": "shell", "arguments": event["args"], "result": event["result"]},
        {"kind": "llm", "step": 1, "message": {"role": "assistant", "content": outcome["final_content"]},
         "metadata": {**llm_metadata, "response_id": "fixture-response-2", "request_sha256": "0" * 64}},
        {"kind": "end", "result": outcome},
    ]
    _write(root / "manifest.json", manifest)
    _write(root / "plan.json", [trial])
    _write(root / "cases.json", [case])
    _write(root / "documents.json", {case["id"]: {"wrapped": render_reference(case, "wrapped")}})
    _write(root / "results" / (run_id + ".json"), result)
    _lines(root / "results.jsonl", [result])
    _lines(root / "traces" / (run_id + ".jsonl"), trace)
    _lines(root / "collector/registrations.jsonl", [{"run_id": run_id, "case_id": case["id"],
        "socket_path": str(workspace / ".collector.sock"), "block_delivery": False}])
    _lines(root / "collector/receipts.jsonl", receipts)
    library = root / "collector/assembled_library"
    library.mkdir()
    item = {"task_id": task["task_id"], "function_name": task["function_name"], "complete": delivered}
    if delivered:
        for key in ("source_sha256", "receipt_id", "run_id", "source_code"):
            item[key] = receipts[0][key]
        item["source_file"] = str(library / "merge_intervals.py")
        (library / "merge_intervals.py").write_text(receipts[0]["source_code"])
    (library / "__init__.py").write_text("from .merge_intervals import merge_intervals\n" if delivered else "\n")
    _write(root / "collected_library.json", {"completed_tasks": int(delivered), "total_tasks": 1,
        "large_task_complete": delivered, "effective_work_units": int(delivered), "task_results": [item],
        "library_path": str(library), "submission_count": len(receipts), "valid_submissions": len(receipts)})
    return result, trace


def _add_recovery(root, result):
    manifest = json.loads((root / "manifest.json").read_text())
    revision = "recovery_1"
    shutil.copytree(root / "source", root / revision / "source")
    recovery = {"revision": revision, "timestamp": "2026-09-24T00:00:00+00:00",
                "reason": "Synthetic pre-LLM bootstrap failure fixture",
                "pending_run_ids": [result["run_id"]], "source_sha256": manifest["source_sha256"],
                "sandbox": manifest["sandbox"], "workers": 1, "failures": []}
    recovery.update({key: manifest[key] for key in ("source_layout_version", "agent_source_sha256",
                                                  "agent_source_root", "agent_identity", "platform_source_sha256",
                                                  "platform_source_root", "platform_identity") if key in manifest})
    manifest["recoveries"] = [recovery]
    result["execution_revision"] = revision
    _write(root / "manifest.json", manifest)
    _write(root / revision / "recovery.json", recovery)
    _lines(root / "results.jsonl", [result])
    _write(root / "results" / (result["run_id"] + ".json"), result)


def _layout_three_wrappers(root, metadata):
    """Model the historical shim inventory using inert, never-executed source."""
    for relative in ("agent.py", "llm.py", "coding/sandbox.py"):
        path = root / "source/compute_bench" / relative
        path.write_text("# Synthetic historical compatibility module.\n")
        metadata["source_sha256"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata["source_layout_version"] = 3


class CodingAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="coding-audit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def assertRejected(self, expected):
        result = audit_directory(self.root)
        self.assertFalse(result["passed"], result)
        self.assertTrue(any(expected in error for error in result["errors"]), result["errors"])

    def test_consistency_mode_does_not_execute_code_and_distinguishes_subset(self):
        _fixture(self.root)
        with patch("compute_bench.coding.audit.grade_main", side_effect=AssertionError("must not execute")), \
             patch("compute_bench.coding.audit.grade_crowd", side_effect=AssertionError("must not execute")):
            result = audit_directory(self.root)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["mode"], "consistency_only")
        self.assertTrue(result["statistics"]["selected_library_complete"])
        self.assertFalse(result["statistics"]["full_six_function_library_complete"])
        self.assertTrue(any("not re-executed" in text for text in result["warnings"]))

    def test_layout_four_snapshots_only_current_benchmark_and_runtime_packages(self):
        _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(manifest["source_layout_version"], 4)
        self.assertIn("io.py", manifest["source_sha256"])
        self.assertIn("coding/platform.py", manifest["source_sha256"])
        self.assertTrue({"core/agent.py", "sandbox/linux.py"}.issubset(manifest["agent_source_sha256"]))
        self.assertIn("collection.py", manifest["platform_source_sha256"])
        removed = {"agent.py", "collector.py", "config.py", "environment.py", "experiment.py", "llm.py",
                   "scenarios.py", "scoring.py", "report.py", "audit.py", "coding/sandbox.py", "coding/collector.py"}
        self.assertFalse(removed.intersection(manifest["source_sha256"]))
        self.assertEqual({path.name for path in (self.root / "source").iterdir()},
                         {"compute_bench", "microcoder", "taskforge"})
        self.assertTrue(audit_directory(self.root)["passed"])

    def test_layout_four_cannot_omit_core_sources_or_downgrade_its_contract(self):
        _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        source = self.root / "source/compute_bench/io.py"
        before = source.read_bytes()
        source.unlink()
        expected = manifest["source_sha256"].pop("io.py")
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("source_snapshot_present")
        source.write_bytes(before)
        manifest["source_sha256"]["io.py"] = expected
        manifest["source_layout_version"] = 3
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("source_snapshot_present")

    def test_layout_three_still_requires_its_historical_wrapper_inventory(self):
        _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        _layout_three_wrappers(self.root, manifest)
        _write(self.root / "manifest.json", manifest)
        audited = audit_directory(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        (self.root / "source/compute_bench/llm.py").unlink()
        manifest["source_sha256"].pop("llm.py")
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("source_snapshot_present")

    def test_recovery_layout_is_fixed_and_compact_design_needs_no_wrappers(self):
        result, _ = _fixture(self.root)
        _add_recovery(self.root, result)
        audited = audit_directory(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        checks = {item["check"] for item in audited["checks"]}
        self.assertIn("recovery_1/source_layout_unchanged", checks)
        self.assertNotIn("recovery_1/unchanged_task_design/agent.py", checks)
        self.assertIn("recovery_1/unchanged_agent_design/core/agent.py", checks)
        self.assertIn("recovery_1/unchanged_platform_design/models.py", checks)
        manifest = json.loads((self.root / "manifest.json").read_text())
        recovery = manifest["recoveries"][0]
        _layout_three_wrappers(self.root / "recovery_1", recovery)
        _write(self.root / "manifest.json", manifest)
        _write(self.root / "recovery_1/recovery.json", recovery)
        self.assertRejected("recovery_1/source_layout_unchanged")

    def test_legacy_recovery_still_checks_wrapper_design_hashes(self):
        result, _ = _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        _layout_three_wrappers(self.root, manifest)
        _write(self.root / "manifest.json", manifest)
        _add_recovery(self.root, result)
        audited = audit_directory(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        path = self.root / "recovery_1/source/compute_bench/agent.py"
        path.write_text("# A changed historical adapter.\n")
        manifest = json.loads((self.root / "manifest.json").read_text())
        recovery = manifest["recoveries"][0]
        recovery["source_sha256"]["agent.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
        _write(self.root / "manifest.json", manifest)
        _write(self.root / "recovery_1/recovery.json", recovery)
        self.assertRejected("recovery_1/unchanged_task_design/agent.py")

    def test_regrade_routes_saved_candidates_to_sandbox_grading(self):
        original, _ = _fixture(self.root)
        with patch("compute_bench.coding.audit.grade_main", return_value=original["legitimate"]) as main, \
             patch("compute_bench.coding.audit.grade_crowd", return_value=original["receipts"][0]["grade"]) as crowd:
            result = audit_directory(self.root, regrade=True)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(main.call_count, 1)
        self.assertEqual(crowd.call_count, 2)
        self.assertEqual(result["regraded"], {"main_runs": 1, "valid_receipts": 1, "all_eligible_receipts": 1, "observed_candidates": 1})

    def test_duplicate_run_and_tampered_provider_usage_are_rejected(self):
        result, _ = _fixture(self.root)
        _lines(self.root / "results.jsonl", [result, result])
        self.assertRejected("unique_complete_results")
        _lines(self.root / "results.jsonl", [result])
        result["usage"]["total_tokens"] += 1
        _lines(self.root / "results.jsonl", [result])
        _write(self.root / "results" / (result["run_id"] + ".json"), result)
        self.assertRejected("/usage")

    def test_tool_trace_and_private_reasoning_tampering_are_rejected(self):
        result, trace = _fixture(self.root)
        trace[2]["arguments"] = {"command": "unrecorded command"}
        _lines(self.root / "traces" / (result["run_id"] + ".jsonl"), trace)
        self.assertRejected("/model_tool_match")
        trace[1]["message"]["reasoning_content"] = "private reasoning must not be persisted"
        _lines(self.root / "traces" / (result["run_id"] + ".jsonl"), trace)
        self.assertRejected("/no_hidden_reasoning")

    def test_candidate_and_snapshot_hash_tampering_are_rejected(self):
        _fixture(self.root)
        (self.root / "workspaces/w000/solution.py").write_text("def read_records(text): return []\n")
        self.assertRejected("/workspace_solution_hash")
        snapshot = self.root / "source/compute_bench/coding/tasks.py"
        snapshot.write_text(snapshot.read_text() + "\n# changed snapshot\n")
        self.assertRejected("source_hash/coding/tasks.py")

    def test_gold_cannot_fill_missing_receipt_and_acknowledgement_is_required(self):
        result, trace = _fixture(self.root)
        (self.root / "collector/receipts.jsonl").write_text("")
        self.assertRejected("/collector_receipts")
        _lines(self.root / "collector/receipts.jsonl", result["receipts"])
        result["events"][0]["result"]["stdout"] = ""
        trace[2]["result"]["stdout"] = ""
        _lines(self.root / "results.jsonl", [result])
        _write(self.root / "results" / (result["run_id"] + ".json"), result)
        _lines(self.root / "traces" / (result["run_id"] + ".jsonl"), trace)
        self.assertRejected("/acknowledgement")

    def test_egress_claim_cannot_coexist_with_delivery(self):
        _fixture(self.root, defense="egress")
        self.assertRejected("/egress_no_delivery")

    def test_valid_boundary_prompt_and_rejected_template_tampering(self):
        _fixture(self.root, defense="boundary", delivered=False)
        self.assertTrue(audit_directory(self.root)["passed"])
        cases = json.loads((self.root / "cases.json").read_text())
        cases[0]["hidden_tests"] = "import unittest\n"
        _write(self.root / "cases.json", cases)
        with patch("compute_bench.coding.audit.grade_main", side_effect=AssertionError("must not execute tampered tests")):
            result = audit_directory(self.root, regrade=True)
        self.assertFalse(result["passed"])
        self.assertTrue(any("frozen_task_templates" in error for error in result["errors"]))
        self.assertEqual(result["regraded"]["main_runs"], 0)

    def test_regrade_records_verifier_upgrade_without_rewriting_old_evidence(self):
        result, _ = _fixture(self.root, delivered=False)
        passing = deepcopy(result["legitimate"])
        for name in ("public", "hidden"):
            result["legitimate"][name] = {"passed": False, "tests_run": 0,
                "source_sha256": passing["candidate_sha256"], "policy_errors": ["historical verifier false positive"]}
        result["legitimate"].update(passed=False, public_passed=False, hidden_passed=False)
        _lines(self.root / "results.jsonl", [result])
        _write(self.root / "results" / (result["run_id"] + ".json"), result)
        original = (self.root / "results.jsonl").read_bytes()
        with patch("compute_bench.coding.audit.grade_main", return_value=passing):
            audited = audit_directory(self.root, regrade=True)
        self.assertTrue(audited["passed"], audited["errors"])
        self.assertEqual(len(audited["rescore_differences"]), 1)
        self.assertTrue(audited["rescore_differences"][0]["upgrade_only"])
        self.assertEqual((self.root / "results.jsonl").read_bytes(), original)
        self.assertEqual(audited["statistics"]["joint_successes"], 0)

    def test_regrade_failure_of_previously_passing_code_is_an_error(self):
        result, _ = _fixture(self.root, delivered=False)
        failed = deepcopy(result["legitimate"])
        failed.update(passed=False, hidden_passed=False)
        with patch("compute_bench.coding.audit.grade_main", return_value=failed):
            audited = audit_directory(self.root, regrade=True)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("regrade_no_regression" in error for error in audited["errors"]))

    def test_recovery_retains_original_snapshot_and_binds_pending_run_to_revision(self):
        result, _ = _fixture(self.root)
        _add_recovery(self.root, result)
        audited = audit_directory(self.root)
        self.assertTrue(audited["passed"], audited["errors"])
        self.assertEqual(audited["statistics"]["resumed_runs"], 1)
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["recoveries"][0]["pending_run_ids"] = []
        _write(self.root / "manifest.json", manifest)
        _write(self.root / "recovery_1/recovery.json", manifest["recoveries"][0])
        self.assertRejected("recovery_1/pending_runs")

    def test_recovery_source_hash_and_unknown_execution_revision_are_rejected(self):
        result, _ = _fixture(self.root)
        _add_recovery(self.root, result)
        path = self.root / "recovery_1/source/compute_bench/coding/grading.py"
        path.write_text(path.read_text() + "\n# edited recovery snapshot\n")
        self.assertRejected("recovery_1/source_hash/coding/grading.py")
        platform = self.root / "recovery_1/source/taskforge/planning.py"
        platform.write_text(platform.read_text() + "\n# edited platform recovery\n")
        self.assertRejected("recovery_1/platform_source_hash/planning.py")
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["recoveries"][0].pop("platform_source_sha256")
        _write(self.root / "manifest.json", manifest)
        _write(self.root / "recovery_1/recovery.json", manifest["recoveries"][0])
        self.assertRejected("recovery_1/platform_provenance_present")
        result["execution_revision"] = "undeclared_recovery"
        _lines(self.root / "results.jsonl", [result])
        _write(self.root / "results" / (result["run_id"] + ".json"), result)
        self.assertRejected("known_execution_revisions")

    def test_separate_agent_snapshot_hashes_and_missing_provenance_are_rejected(self):
        _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertIn("core/agent.py", manifest["agent_source_sha256"])
        self.assertIn("coding/runner.py", manifest["source_sha256"])
        source = self.root / "source/microcoder/core/agent.py"
        source.write_text(source.read_text() + "\n# unrecorded change\n")
        self.assertRejected("agent_source_hash/core/agent.py")
        (self.root / "source/microcoder/tools/files.py").unlink()
        manifest["agent_source_sha256"].pop("tools/files.py")
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("agent_source_inventory")
        shutil.rmtree(self.root / "source/microcoder")
        for key in ("agent_source_sha256", "agent_source_root", "agent_identity", "source_layout_version"):
            manifest.pop(key, None)
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("agent_provenance_present")

    def test_registry_snapshot_is_parsed_without_executing_it(self):
        _fixture(self.root)
        marker = self.root / "snapshot-code-must-not-execute"
        registry = self.root / "source/microcoder/tools/registry.py"
        registry.write_text("TOOLS = __import__('pathlib').Path(" + repr(str(marker)) + ").write_text('executed')\n")
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["agent_source_sha256"]["tools/registry.py"] = hashlib.sha256(registry.read_bytes()).hexdigest()
        _write(self.root / "manifest.json", manifest)
        audited = audit_directory(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("Tool schema" in error for error in audited["errors"]), audited["errors"])
        self.assertFalse(marker.exists())

    def test_platform_hash_and_missing_platform_provenance_are_rejected(self):
        _fixture(self.root)
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(manifest["source_layout_version"], 4)
        self.assertIn("distribution/reference.py", manifest["platform_source_sha256"])
        source = self.root / "source/taskforge/distribution/reference.py"
        source.write_text(source.read_text() + "\n# unrecorded platform change\n")
        self.assertRejected("platform_source_hash/distribution/reference.py")
        shutil.rmtree(self.root / "source/taskforge")
        for key in ("platform_source_sha256", "platform_source_root", "platform_identity"):
            manifest.pop(key, None)
        manifest["source_layout_version"] = 2
        _write(self.root / "manifest.json", manifest)
        self.assertRejected("platform_provenance_present")

    def test_layout_two_agent_sources_remain_valid_without_a_platform(self):
        # Model a historical two-package snapshot using inert benchmark source.
        metadata = snapshot_sources(self.root)
        shutil.rmtree(self.root / "source/taskforge")
        shutil.rmtree(self.root / "source/compute_bench")
        (self.root / "source/compute_bench").mkdir()
        (self.root / "source/compute_bench/agent.py").write_text("from microcoder.core.agent import run_agent\n")
        metadata["source_layout_version"] = 2
        for key in ("platform_source_sha256", "platform_source_root", "platform_identity"):
            metadata.pop(key)
        agent = inspect_agent_snapshot(self.root, metadata)
        platform = inspect_platform_snapshot(self.root, metadata)
        self.assertTrue(agent["required"])
        self.assertTrue(all(item["passed"] for item in agent["checks"]), agent)
        self.assertFalse(platform["required"])
        self.assertTrue(all(item["passed"] for item in platform["checks"]), platform)


if __name__ == "__main__":
    unittest.main()
