"""Corrected schema-v2 evidence remains anchored to raw runs."""

import json
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.audit import audit_corrected
from compute_bench.coding.rescore import rescore_directory
from tests.test_coding_audit import _fixture


class CorrectedAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="coding-corrected-v2-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_rescore_and_corrected_regrade_pass(self):
        _fixture(self.root, delivered=True)
        correction = rescore_directory(self.root, workers=1)
        self.assertEqual(correction["completed_work_units"], 1)
        result = audit_corrected(self.root, regrade=True)
        self.assertTrue(result["passed"], result["errors"])

    def test_corrected_trajectory_tampering_is_rejected(self):
        _fixture(self.root)
        rescore_directory(self.root, workers=1)
        path = self.root / "corrected_results.jsonl"
        result = json.loads(path.read_text())
        result["final_content"] = "changed"
        path.write_text(json.dumps(result) + "\n")
        correction = json.loads((self.root / "evaluation_corrections.json").read_text())
        import hashlib
        correction["corrected_results_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / "evaluation_corrections.json").write_text(json.dumps(correction))
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("immutable_trajectory" in error for error in audited["errors"]))

    def test_verified_artifact_tampering_is_rejected(self):
        _fixture(self.root, delivered=True)
        correction = rescore_directory(self.root, workers=1)
        item = next(entry for entry in correction["task_results"] if entry["complete"])
        (self.root / "verified_artifacts" / (item["task_id"] + ".json")).write_text("{}")
        audited = audit_corrected(self.root)
        self.assertFalse(audited["passed"])
        self.assertTrue(any("verified_file" in error for error in audited["errors"]))


if __name__ == "__main__":
    unittest.main()
