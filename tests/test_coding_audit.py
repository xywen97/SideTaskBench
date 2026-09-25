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


def _fixture(root: Path, defense="none", delivered=False):
    def run(agent, task, trace):
        case, workspace = agent.tools.case, agent.tools.workspace
        (workspace / "solution.py").write_text(case["reference_files"]["solution.py"])
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
        execute_coding(Settings(api_key="fixture", model="fixture-model"), root, count=1,
                       conditions=["wrapped"], defenses=[defense], repeats=1, workers=1)
    result = json.loads((root / "results.jsonl").read_text())
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
