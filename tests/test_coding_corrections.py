"""Post-hoc regrading for generic atomic artifacts."""

import json
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.rescore import rescore_directory
from compute_bench.coding.runner import scan_work
from compute_bench.coding.tasks import build_coding_cases
from tests.test_coding_audit import _fixture


class CorrectedAcceptanceTests(unittest.TestCase):
    def test_rescore_keeps_raw_results_and_writes_v3_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root, delivered=True)
            before = (root / "results.jsonl").read_bytes()
            correction = rescore_directory(root, workers=1)
            self.assertEqual((root / "results.jsonl").read_bytes(), before)
            self.assertEqual(correction["evaluation_version"], "coding_atomic_acceptance_v3")
            self.assertEqual(correction["completed_work_units"], 1)
            self.assertTrue((root / "verified_artifacts").is_dir())

    def test_rescore_rejects_modified_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root)
            (root / "workspaces/w000/solution.py").write_text("# modified\n")
            with self.assertRaisesRegex(ValueError, "inconsistent original evidence"):
                rescore_directory(root, workers=1)
            self.assertFalse((root / "corrected_results.jsonl").exists())

    def test_scan_work_finds_deleted_file_artifact_from_write_event(self):
        case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
        path, content = next(iter(case["crowd_reference_artifact"]["files"].items()))
        event = {"tool": "write_file", "args": {"path": "/workspace/reference_work/" + path, "content": content},
                 "result": {"written": "reference_work/" + path, "bytes": len(content.encode()),
                            "sha256": __import__("hashlib").sha256(content.encode()).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            observed = scan_work(case, Path(directory), [event])
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0]["grade"]["passed"])
        self.assertEqual(observed[0]["provenance"], "trace_write_file")

    def test_scan_work_finds_json_submission_envelope(self):
        case = build_coding_cases(host_task_ids=["coding-05"], atomic_task_ids=["classify-timeout-event"])[0]
        payload = {"task_id": case["crowd_task"]["task_id"], "artifact": case["crowd_reference_artifact"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "payload.json").write_text(json.dumps(payload))
            observed = scan_work(case, root)
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0]["grade"]["passed"])


if __name__ == "__main__":
    unittest.main()
