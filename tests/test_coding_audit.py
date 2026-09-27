"""Tamper checks for schema-v2 coding evidence."""

import http.client
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.audit import audit_directory
from compute_bench.coding.runner import execute_coding
from microcoder.config import Settings


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("collector", timeout=5)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(self.path))


def _fixture(root: Path, defense="none", delivered=False, rejected_payloads=(),
             host_task_ids=None, atomic_task_ids=None, repeats=1,
             conditions=None, inspect_agent=None):
    def run(agent, task, trace):
        case, workspace = agent.tools.case, agent.tools.workspace
        if inspect_agent:
            inspect_agent(agent)
        (workspace / "solution.py").write_text(case["reference_files"]["solution.py"])
        for payload in rejected_payloads:
            connection = _UnixConnection(workspace / ".collector.sock")
            connection.request("POST", "/submit", json.dumps(payload),
                               {"Content-Type": "application/json"})
            response = connection.getresponse()
            assert json.loads(response.read())["valid"] is False
            connection.close()
        if delivered:
            connection = _UnixConnection(workspace / ".collector.sock")
            connection.request("POST", "/submit", json.dumps({
                "task_id": case["crowd_task"]["task_id"],
                "artifact": case["crowd_reference_artifact"],
            }), {"Content-Type": "application/json"})
            response = connection.getresponse()
            assert json.loads(response.read())["valid"]
            connection.close()
        trace.parent.mkdir(parents=True, exist_ok=True)
        trace.write_text('{"kind":"synthetic-v2"}\n')
        return {"status": "completed", "error": None, "final_content": "fixture",
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "reasoning_tokens": 0},
                "llm_calls": 1, "tool_calls": 0, "latency_seconds": .01,
                "api_response_ids": ["fixture"], "trace_file": str(trace), "provider_truncated": False}

    with patch("compute_bench.coding.runner.ChatClient"), \
         patch("compute_bench.coding.runner.CodingAgent.run", autospec=True, side_effect=run), \
         patch("builtins.print"):
        execute_coding(Settings(api_key="fixture", model="fixture-model"), root,
                       host_task_ids=host_task_ids or ["coding-01"],
                       atomic_task_ids=atomic_task_ids or ["rewrite-user-record"],
                       conditions=conditions or ["wrapped"], defenses=[defense], repeats=repeats, workers=1)
    result = json.loads((root / "results.jsonl").read_text().splitlines()[0])
    return result, []


class CodingAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="coding-audit-v2-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_valid_consistency_and_sandbox_regrade(self):
        _fixture(self.root, delivered=True)
        plain = audit_directory(self.root)
        self.assertTrue(plain["passed"], plain["errors"])
        self.assertEqual(plain["statistics"]["atomic_catalog_size"], 30)
        regraded = audit_directory(self.root, regrade=True)
        self.assertTrue(regraded["passed"], regraded["errors"])
        self.assertEqual(regraded["regraded"]["valid_receipts"], 1)

    def test_case_task_tampering_is_rejected(self):
        _fixture(self.root)
        cases = json.loads((self.root / "cases.json").read_text())
        cases[0]["crowd_task"]["description"] += " tampered"
        (self.root / "cases.json").write_text(json.dumps(cases))
        result = audit_directory(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("frozen_task_templates" in error for error in result["errors"]))

    def test_rejected_submissions_are_evidence_not_corruption(self):
        from compute_bench.coding.tasks import build_coding_cases
        case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
        payloads = [
            {},
            {"task_id": case["crowd_task"]["task_id"]},
            {"task_id": "wrong-task", "artifact": case["crowd_reference_artifact"]},
            {"artifact": case["crowd_reference_artifact"]},
        ]
        payloads.extend(
            {"task_id": case["crowd_task"]["task_id"], "artifact": artifact}
            for artifact in [
                {"kind": "files", "files": {}},
                {"kind": "bogus", "files": {"unit.py": "pass"}},
                {"kind": "files", "files": {"unit.py": 123}},
                {"kind": "files", "files": {"/unit.py": "pass"}},
                {"kind": "files", "files": {"unit.py": "pass"}, "language": "python"},
            ]
        )
        _fixture(self.root, delivered=True, rejected_payloads=payloads)
        for regrade in (False, True):
            with self.subTest(regrade=regrade):
                audited = audit_directory(self.root, regrade=regrade)
                self.assertTrue(audited["passed"], audited["errors"])
                self.assertEqual(audited["statistics"]["receipts"], len(payloads) + 1)
                self.assertEqual(audited["statistics"]["valid_receipts"], 1)
                if regrade:
                    self.assertEqual(audited["regraded"]["all_eligible_receipts"], 1)
                    self.assertEqual(audited["regraded"]["valid_receipts"], 1)

    def _edit_first_receipt(self, edit):
        path = self.root / "collector/receipts.jsonl"
        receipt = json.loads(path.read_text())
        edit(receipt)
        path.write_text(json.dumps(receipt) + "\n")
        # Keep duplicate records in sync to exercise the receipt checks rather
        # than merely the collector/results equality check.
        path = self.root / "results.jsonl"
        result = json.loads(path.read_text())
        result["receipts"] = [receipt]
        path.write_text(json.dumps(result) + "\n")

    def test_rejected_submission_hash_tampering_is_rejected(self):
        _fixture(self.root, rejected_payloads=[{}])
        self._edit_first_receipt(lambda receipt: receipt.update(artifact_sha256="0" * 64))
        audited = audit_directory(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("/hash" in error for error in audited["errors"]))

    def test_invalid_submission_cannot_be_marked_successful(self):
        _fixture(self.root, rejected_payloads=[{}])
        self._edit_first_receipt(lambda receipt: receipt.update(valid=True, grade={"passed": True}))
        audited = audit_directory(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("/submission_eligibility" in error for error in audited["errors"]))
        self.assertTrue(any("/valid_flag" in error for error in audited["errors"]))

    def test_wrong_task_cannot_claim_a_passing_grade(self):
        _fixture(self.root, delivered=True)
        self._edit_first_receipt(lambda receipt: receipt.update(task_id="wrong-task"))
        audited = audit_directory(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("/submission_eligibility" in error for error in audited["errors"]))

    def test_receipt_for_unknown_run_is_rejected(self):
        _fixture(self.root, rejected_payloads=[{}])
        self._edit_first_receipt(lambda receipt: receipt.update(run_id="unknown-run"))
        audited = audit_directory(self.root)
        self.assertFalse(audited["passed"])
        self.assertIn("receipt_assignments", audited["errors"])

    def test_artifact_hash_and_flag_tampering_are_rejected(self):
        _fixture(self.root, delivered=True)
        receipts = [json.loads(line) for line in (self.root / "collector/receipts.jsonl").read_text().splitlines()]
        receipts[0]["artifact_sha256"] = "0" * 64
        (self.root / "collector/receipts.jsonl").write_text(json.dumps(receipts[0]) + "\n")
        result = audit_directory(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("/hash" in error for error in result["errors"]))

    def test_solution_tampering_is_rejected(self):
        _fixture(self.root)
        (self.root / "workspaces/w000/solution.py").write_text("# changed after run\n")
        result = audit_directory(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("workspace_solution_hash" in error for error in result["errors"]))

    def test_portfolio_output_tampering_is_rejected(self):
        _fixture(self.root, delivered=True)
        output = next(path for path in (self.root / "platform/result/artifacts").rglob("*") if path.is_file())
        output.write_text("changed")
        result = audit_directory(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("portfolio_output_hashes" in error for error in result["errors"]))

    def test_egress_has_no_receipt(self):
        _fixture(self.root, defense="egress", delivered=False)
        result = audit_directory(self.root)
        self.assertTrue(result["passed"], result["errors"])


if __name__ == "__main__":
    unittest.main()
