"""Full-cross identities survive delivery, reporting, regrading and missing runs."""

import json
from pathlib import Path
import tempfile
import unittest

from compute_bench.coding.audit import audit_directory, audit_corrected
from compute_bench.coding.report import write_report
from compute_bench.coding.rescore import rescore_directory
from tests.test_coding_audit import _fixture


class CodingMatrixTests(unittest.TestCase):
    def test_two_by_two_pairs_deliver_without_collisions_and_deduplicate_units(self):
        with tempfile.TemporaryDirectory(prefix="matrix-") as tmp:
            root = Path(tmp)
            hosts = ["coding-01", "coding-02"]
            atomic = ["rewrite-user-record", "regression-empty-page"]
            _fixture(root, delivered=True, host_task_ids=hosts, atomic_task_ids=atomic, repeats=2)
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertNotIn("pairing_rotation", manifest)
            self.assertEqual(manifest["pair_count"], 4)
            results = [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines()]
            self.assertEqual(len(results), 8)
            self.assertEqual(len({r["run_id"] for r in results}), 8)
            self.assertEqual(len({r["workspace_id"] for r in results}), 8)
            self.assertEqual({(r["host_task_id"], r["atomic_task_id"]) for r in results},
                             {(h, t) for h in hosts for t in atomic})
            for result in results:
                self.assertTrue(result["joint_success"])
                receipt = result["receipts"][0]
                self.assertEqual(receipt["case_id"], result["case_id"])
                self.assertEqual(receipt["task_id"], result["atomic_task_id"])
            comparisons = json.loads((root / "reference_comparisons/index.json").read_text())
            self.assertEqual(len(comparisons), 4)
            self.assertEqual(len({item["after"] for item in comparisons}), 4)
            for item in comparisons:
                self.assertIn(item["task_id"], (root / item["after"]).read_text())
            pairs = json.loads((root / "pair_results.json").read_text())
            self.assertEqual(len(pairs), 4)
            self.assertTrue(all(p["runs"] == p["planned_runs"] == p["joint_success"] == 2 for p in pairs))
            summary = json.loads((root / "summary.json").read_text())
            self.assertTrue(summary["groups"][0]["complete_selected_set"])
            self.assertEqual(summary["groups"][0]["unique_work_units"], 2)
            audited = audit_directory(root, regrade=True)
            self.assertTrue(audited["passed"], audited["errors"])
            correction = rescore_directory(root, workers=1)
            self.assertEqual(correction["selected_work_units"], 2)
            self.assertEqual(len(correction["task_results"]), 2)
            self.assertTrue(correction["selected_set_complete"])
            corrected = audit_corrected(root, regrade=True)
            self.assertTrue(corrected["passed"], corrected["errors"])
            write_report(root, corrected=True)
            self.assertEqual(len(json.loads((root / "corrected_pair_results.json").read_text())), 4)
            # A missing pair must remain visible rather than disappearing from the report.
            (root / "results.jsonl").write_text("\n".join(json.dumps(r) for r in results if r["case_id"] != results[0]["case_id"]) + "\n")
            summary = write_report(root)
            self.assertFalse(summary["all_planned_recorded"])
            pairs = json.loads((root / "pair_results.json").read_text())
            missing = next(p for p in pairs if p["case_id"] == results[0]["case_id"])
            self.assertEqual(missing["runs"], 0)
            self.assertEqual(missing["missing_runs"], 2)
            self.assertIsNone(missing["mean_total_tokens"])


if __name__ == "__main__":
    unittest.main()
