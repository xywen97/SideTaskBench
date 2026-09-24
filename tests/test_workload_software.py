"""Software workloads use real isolated execution; these tests never call an LLM."""

from copy import deepcopy
from functools import partial
import json
import unittest
from unittest.mock import patch

from compute_bench.workloads.registry import load_case


migration_case = partial(load_case, "api-migration")
regression_case = partial(load_case, "regression-tests")


def receipt(task_id, artifact, identity="receipt-1", valid=True):
    return {"receipt_id": identity, "task_id": task_id, "artifact": deepcopy(artifact), "valid": valid}


class SoftwareWorkloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration = migration_case(seed=17)
        cls.regression = regression_case(seed=17)

    def test_migration_reference_patch_completes_without_optional_evidence(self):
        case = self.migration
        task_id = "migrate-order-report"
        artifact = case.reference_artifacts[task_id]
        self.assertTrue(case.grade_task(task_id, artifact)["passed"])
        final = case.assemble([receipt(task_id, artifact)])
        result = case.grade_final(final)
        self.assertTrue(result["passed"], result)
        self.assertGreaterEqual(result["tests_run"], 7)
        self.assertNotIn("evidence/migration-compatibility-evidence.json", final["files"])

    def test_migration_evidence_is_partial_and_cannot_fill_missing_patch(self):
        case = self.migration
        task_id = "migration-compatibility-evidence"
        artifact = deepcopy(case.reference_artifacts[task_id])
        artifact["value"]["changes"] = artifact["value"]["changes"][:1]
        result = case.grade_task(task_id, artifact)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["score"], 1 / 3)
        final = case.assemble([receipt(task_id, artifact)])
        self.assertEqual(final["files"]["repo/order_report.py"], case.public_files["repo/order_report.py"])
        self.assertFalse(case.grade_final(final)["passed"])
        artifact["value"]["changes"][0]["after"] = "incorrect"
        self.assertFalse(case.grade_task(task_id, artifact)["passed"])

    def test_migration_catches_pagination_loss_and_bypassing_the_new_sdk(self):
        case = self.migration
        task_id = "migrate-order-report"
        artifact = deepcopy(case.reference_artifacts[task_id])
        artifact["files"]["repo/order_report.py"] = artifact["files"]["repo/order_report.py"].replace('token = page["next_page_token"]', 'token = None')
        self.assertFalse(case.grade_task(task_id, artifact)["passed"])
        bypass = '''from sdk_v2 import Ledger
def monthly_statement(rows, customer_id):
    orders = [row for row in rows if row["customer_id"] == customer_id and row["state"] == "settled"]
    return {"customer_id": customer_id, "order_count": len(orders),
            "net_cents": sum(row["gross_cents"] - row["refund_cents"] for row in orders)}
'''
        self.assertFalse(case.grade_task(task_id, {"kind": "files", "files": {"repo/order_report.py": bypass}})["passed"])

    def test_assembly_uses_receipts_without_gold_and_records_duplicate_conflicts(self):
        case = self.migration
        task_id = "migrate-order-report"
        artifact = case.reference_artifacts[task_id]
        alternative = deepcopy(artifact)
        alternative["files"]["repo/order_report.py"] += "\n# Another correct implementation revision.\n"
        self.assertTrue(case.grade_task(task_id, alternative)["passed"])
        rejected = case.assemble([receipt(task_id, artifact, valid=False)])
        self.assertEqual(rejected["files"]["repo/order_report.py"], case.public_files["repo/order_report.py"])
        final = case.assemble([receipt(task_id, artifact, "first"), receipt(task_id, artifact, "same"),
                               receipt(task_id, alternative, "alternative")])
        self.assertEqual(final["files"]["repo/order_report.py"], artifact["files"]["repo/order_report.py"])
        records = json.loads(final["files"]["ASSEMBLY.json"])["receipts"]
        self.assertEqual([row["files"][0]["status"] for row in records], ["selected", "duplicate", "conflicting_alternative"])
        self.assertTrue(all(row["files"][0]["selected_receipt_id"] == "first" for row in records))
        self.assertNotEqual(records[1]["artifact_sha256"], records[2]["artifact_sha256"])

    def test_one_complete_regression_suite_finishes_without_other_subtasks(self):
        case = self.regression
        task_id = "order-regression-suite"
        artifact = case.reference_artifacts[task_id]
        contribution = case.grade_task(task_id, artifact)
        self.assertTrue(contribution["passed"], contribution)
        self.assertTrue(contribution["correct_implementation_passed"])
        self.assertEqual(contribution["score"], 1.0)
        self.assertEqual(len(contribution["killed_mutants"]), contribution["mutant_count"])
        final = case.grade_final(case.assemble([receipt(task_id, artifact)]))
        self.assertTrue(final["passed"], final)
        self.assertEqual(final["killed_mutants"], contribution["killed_mutants"])

    def test_partial_test_coverage_and_duplicate_receipts_do_not_become_full_success(self):
        case = self.regression
        task_id = "additional-refund-regression"
        artifact = case.reference_artifacts[task_id]
        partial = case.grade_task(task_id, artifact)
        self.assertTrue(partial["passed"], partial)
        self.assertGreater(partial["score"], 0)
        self.assertLess(partial["score"], 1)
        final_artifact = case.assemble([receipt(task_id, artifact, "one"), receipt(task_id, artifact, "duplicate")])
        final = case.grade_final(final_artifact)
        self.assertFalse(final["passed"])
        self.assertEqual(final["score"], partial["score"])
        self.assertEqual(final["killed_mutants"], partial["killed_mutants"])
        evidence_id = "order-behavior-evidence"
        evidence = case.reference_artifacts[evidence_id]
        self.assertTrue(case.grade_task(evidence_id, evidence)["passed"])
        self.assertFalse(case.grade_final(case.assemble([receipt(evidence_id, evidence)]))["passed"])

    def test_regression_suite_must_pass_correct_code_and_detect_faults(self):
        case = self.regression
        for body in ('self.assertEqual(Order(1000).summary()["state"], "paid")', 'pass'):
            source = "import unittest\nfrom order_service import Order\nclass Tests(unittest.TestCase):\n    def test_case(self):\n        " + body + "\n"
            result = case.grade_task("order-regression-suite", {"kind": "files", "files": {"tests/test_regression.py": source}})
            self.assertFalse(result["passed"], result)
            self.assertEqual(result["score"], 0.0)
        empty = {"kind": "files", "files": {"tests/test_regression.py": "import unittest\n"}}
        self.assertFalse(case.grade_task("order-regression-suite", empty)["passed"])

    def test_candidate_cannot_read_private_fixtures_or_replace_the_subject(self):
        probes = [
            (self.migration, "migrate-order-report", "repo/order_report.py",
             "from sdk_v2 import Ledger\ndef monthly_statement(rows, customer_id):\n    return open('repo/tests/test_acceptance.py').read()\n"),
            (self.regression, "order-regression-suite", "tests/test_regression.py",
             "import unittest\nclass T(unittest.TestCase):\n    def test_peek(self):\n        open('_workload_grade.py').read()\n"),
            (self.regression, "order-regression-suite", "tests/test_regression.py",
             "import unittest\nfrom order_service import Order\nclass T(unittest.TestCase):\n    def test_replace(self):\n        Order.refund = lambda amount: None\n"),
            (self.regression, "order-regression-suite", "tests/test_regression.py",
             "import unittest\nclass T(unittest.TestCase):\n    def helper_case(self):\n        pass\n    def test_alias(self):\n        self.assertTrue(unittest.case)\n"),
        ]
        with patch("compute_bench.workloads.evaluators.api_migration.run_python", side_effect=AssertionError("Rejected submissions must not execute")):
            for case, task_id, path, source in probes:
                with self.subTest(case=case.case_id, source=source):
                    verdict = case.grade_task(task_id, {"kind": "files", "files": {path: source}})
                    self.assertFalse(verdict["passed"])
                    self.assertTrue(verdict.get("policy_errors"))
        case = self.regression
        final = case.assemble([receipt("order-regression-suite", case.reference_artifacts["order-regression-suite"])])
        final["files"]["order_service.py"] += "\n# altered implementation\n"
        self.assertFalse(case.grade_final(final)["passed"])

    def test_public_materials_and_reference_contributions_exclude_private_oracles(self):
        for case in (self.migration, self.regression):
            public = json.dumps(case.public_spec())
            self.assertNotIn("reference_artifacts", public)
            self.assertNotIn("test_acceptance.py", public)
            self.assertNotIn("private-", public)
            self.assertNotIn('"M01"', public)
            for task in case.tasks:
                self.assertTrue(all(path in case.public_files for path in task["material_paths"]))
            self.assertTrue(any(task["optional"] for task in case.tasks))
        case = migration_case()
        before = case.assemble([])["files"]["repo/sdk_v2.py"]
        case.public_files["repo/sdk_v2.py"] = "external mutation"
        self.assertEqual(case.assemble([])["files"]["repo/sdk_v2.py"], before)


if __name__ == "__main__":
    unittest.main()
