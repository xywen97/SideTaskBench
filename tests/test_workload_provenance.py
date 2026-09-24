"""A trusted migration must pin both old and current code and public resources."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.workloads import provenance
from compute_bench.workloads.registry import CASE_MODULES


class WorkloadMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wl-migration-test-")
        self.certificate_file = Path(self.temporary.name) / "trusted-test-certificate.json"
        self.certificate = json.loads(provenance.MIGRATION_FILE.read_text())
        self.certificate["status"] = "verified"
        self.certificate["current_source_sha256"] = provenance.current_evaluator_hashes(self.certificate["case_ids"])
        self.certificate["current_resource_sha256"] = provenance.current_resource_hashes(self.certificate["case_ids"])
        self.manifest = {"case_ids": self.certificate["case_ids"], "seed": 0,
                         "public_spec_sha256": {case_id: hashes["0"] for case_id, hashes in
                                                self.certificate["public_spec_sha256"].items()}}
        for package, field in provenance.SOURCE_FIELDS.items():
            self.manifest[field] = copy.deepcopy(self.certificate["legacy_source_sha256"][package])
        self.save()
        self.patched = patch.object(provenance, "MIGRATION_FILE", self.certificate_file)
        self.patched.start()

    def tearDown(self):
        self.patched.stop()
        self.temporary.cleanup()

    def save(self):
        self.certificate_file.write_text(json.dumps(self.certificate))

    def test_exact_known_migration_matches_without_loading_snapshot(self):
        result = provenance.migration_matches(self.manifest)
        self.assertEqual(result["migration_id"], "python-cases-to-json-v1")

    def test_pending_certificate_cannot_authorize_regrade(self):
        self.certificate["status"] = "pending"
        self.save()
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_unknown_legacy_snapshot_does_not_match(self):
        self.manifest["source_sha256"]["workloads/cases/api_migration.py"] = "0" * 64
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_missing_dependency_cannot_shrink_the_gate(self):
        self.certificate["legacy_source_sha256"]["compute_bench"].pop("workloads/cases/api_migration.py")
        self.save()
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_current_source_change_does_not_match(self):
        self.certificate["current_source_sha256"]["compute_bench"]["workloads/definitions.py"] = "0" * 64
        self.save()
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_current_material_change_does_not_match(self):
        self.certificate["current_resource_sha256"]["order_reconciliation/materials/README.md"] = "0" * 64
        self.save()
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_unknown_seed_does_not_match(self):
        self.manifest["seed"] = 123
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_changed_public_spec_does_not_match(self):
        self.manifest["public_spec_sha256"]["api-migration"] = "0" * 64
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_new_run_cannot_fall_back_to_legacy_bridge(self):
        self.manifest["workload_definition_version"] = 1
        self.assertIsNone(provenance.migration_matches(self.manifest))

    def test_run_provided_certificate_has_no_authority(self):
        self.certificate_file.unlink()
        self.manifest["migration_certificate"] = self.certificate
        self.assertIsNone(provenance.migration_matches(self.manifest))


if __name__ == "__main__":
    unittest.main()
