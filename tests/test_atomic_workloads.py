"""Closed packets, isolated grading and actual-result assembly; no model calls."""

import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.cli import main
from compute_bench.workloads.contracts import canonical_hash
from compute_bench.workloads.definitions import _validate, case_definition
from compute_bench.workloads.evaluation import fixture_receipts
from compute_bench.workloads.packets import validate_packet
from compute_bench.workloads.registry import load_case
from compute_bench.workloads import runner
from compute_bench.workloads.audit import audit_directory
from compute_bench.workloads.evaluators.order_reconciliation import _same
from microcoder.config import Settings


IDS = ("api-migration-atomic", "regression-tests-atomic", "order-reconciliation-atomic", "catalog-normalization-atomic")


class AtomicWorkloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {case_id: load_case(case_id) for case_id in IDS}
        cls.receipts = {case_id: fixture_receipts(case) for case_id, case in cls.cases.items()}

    def test_all_43_packets_are_closed_and_independently_accepted(self):
        self.assertEqual([len(self.cases[k].tasks) for k in IDS], [3, 9, 11, 20])
        for case_id, case in self.cases.items():
            self.assertEqual(case.public_files, {})
            for task in case.tasks:
                validate_packet(task)
                self.assertEqual(task["material_paths"], [])
                self.assertEqual(task["packet"]["dependencies"], [])
            self.assertTrue(all(r["valid"] for r in self.receipts[case_id]), case_id)

    def test_actual_contributions_complete_each_T_but_missing_and_rejected_do_not(self):
        for case_id, case in self.cases.items():
            with self.subTest(case_id=case_id):
                receipts = self.receipts[case_id]
                self.assertTrue(case.grade_final(case.assemble(receipts))["passed"])
                self.assertFalse(case.grade_final(case.assemble([]))["passed"])
                self.assertFalse(case.grade_final(case.assemble(receipts[:1]))["passed"])
                rejected = deepcopy(receipts)
                for r in rejected:
                    r.update(valid=False, grade={"passed": False})
                self.assertFalse(case.grade_final(case.assemble(rejected))["passed"])
                # Duplicates never inflate source coverage or add monetary value.
                artifact = case.assemble(receipts + deepcopy(receipts))
                self.assertTrue(case.grade_final(artifact)["passed"])

    def test_data_final_deliverables_match_independent_original_seed0_oracles(self):
        for original in ("order-reconciliation", "catalog-normalization"):
            legacy = load_case(original, 0)
            atomic = self.cases[original + "-atomic"]
            result = atomic.assemble(self.receipts[atomic.case_id])["value"]
            expected = legacy.assemble(fixture_receipts(legacy))["value"]
            for field in (("orders", "summary", "exceptions") if original == "order-reconciliation" else
                          ("entities", "source_map", "uncertain", "summary")):
                self.assertTrue(_same(result[field], expected[field]), original + "/" + field)

    def test_atomic_inputs_are_fixed_json_not_silently_regenerated_by_seed(self):
        for case_id in IDS:
            self.assertEqual(self.cases[case_id].public_spec(), load_case(case_id, 41).public_spec())

    def test_external_dependency_and_malformed_packet_are_rejected(self):
        original = case_definition(IDS[0])
        for change in (lambda t: t.update(material_paths=["README.md"]),
                       lambda t: t["packet"].update(dependencies=["peer-task"]),
                       lambda t: t["packet"].update(runtime="project-installed-sdk"),
                       lambda t: t["packet"].update(version=True),
                       lambda t: t["packet"].update(input={}),
                       lambda t: t["packet"].update(output={})): 
            definition = deepcopy(original)
            change(definition["tasks"][0])
            with self.assertRaises(ValueError):
                _validate(definition)

    def test_function_grader_rejects_imports_mutation_and_incorrect_results(self):
        case = self.cases[IDS[0]]
        task = case.tasks[0]
        for source in ('from sdk_v2 import Ledger\ndef normalize_order(row): return row\n',
                       'def normalize_order(row):\n    row.clear()\n    return {}\n',
                       'def normalize_order(row): return {}\n'):
            self.assertFalse(case.grade_task(task["task_id"], {"kind": "files", "files": {"normalize_order.py": source}})["passed"])

    def test_regression_requires_fault_detection_not_just_a_correct_example(self):
        case = self.cases[IDS[1]]
        task = case.tasks[0]
        harmless = {"kind": "json", "value": task["packet"]["examples"][0]}
        self.assertFalse(case.grade_task(task["task_id"], harmless)["passed"])
        bad = deepcopy(case.reference_artifacts[task["task_id"]])
        bad["value"]["expected"] = {"error": "ValueError", "at_step": 0}
        self.assertFalse(case.grade_task(task["task_id"], bad)["passed"])

    def test_regression_accepts_different_valid_scenarios_for_the_same_behavior(self):
        case = self.cases[IDS[1]]
        receipts = deepcopy(self.receipts[IDS[1]])
        alternative = deepcopy(receipts[0])
        alternative["receipt_id"] = "alternative-real-example"
        alternative["artifact"]["value"]["total_cents"] = 250
        self.assertTrue(case.grade_task(alternative["task_id"], alternative["artifact"])["passed"])
        result = case.assemble(receipts + [alternative])
        metadata = json.loads(result["files"]["ASSEMBLY.json"])
        self.assertEqual(metadata["receipts"][-1]["status"], "accepted_alternative")
        self.assertTrue(case.grade_final(result)["passed"])

    def test_missing_catalog_identity_stays_unresolved_despite_marketing_title(self):
        case = self.cases[IDS[3]]
        task = next(t for t in case.tasks if t["packet"]["input"]["record"]["model"] == "")
        expected = case.reference_artifacts[task["task_id"]]
        self.assertIsNone(expected["value"]["entity_id"])
        altered = deepcopy(expected)
        altered["value"]["entity_id"] = "guessed-from-title"
        self.assertFalse(case.grade_task(task["task_id"], altered)["passed"])

    def test_conflicting_receipts_cannot_silently_complete_data_tasks(self):
        for case_id in IDS[2:]:
            case = self.cases[case_id]
            receipts = deepcopy(self.receipts[case_id])
            other = deepcopy(receipts[0])
            other["artifact"]["value"]["invented"] = True
            result = case.assemble(receipts + [other])
            self.assertTrue(result["value"]["assembly_conflicts"])
            self.assertFalse(case.grade_final(result)["passed"])

    def test_cli_packet_exports_one_task_without_other_task_inputs(self):
        task = self.cases[IDS[0]].tasks[0]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            main(["workloads", "packet", IDS[0], task["task_id"]])
        self.assertEqual(json.loads(output.getvalue()), task)
        self.assertNotIn(self.cases[IDS[0]].tasks[1]["task_id"], output.getvalue())


class ClosedWorkspaceTests(unittest.TestCase):
    def test_runner_inlines_one_packet_without_materials_or_peer_tasks(self):
        inputs = []

        class FakeClient:
            def __init__(self, settings):
                pass

            def complete(self, messages, tools):
                inputs.append(deepcopy(messages))
                return ({"role": "assistant", "content": "Fixture: no extra work performed."},
                        {"response_id": "fake-closed-" + str(len(inputs)),
                         "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})

            def close(self):
                pass

        with tempfile.TemporaryDirectory(prefix="atomic-") as tmp, patch.object(runner, "ChatClient", FakeClient), \
             contextlib.redirect_stdout(io.StringIO()):
            settings = Settings(api_key="fixture-no-network")
            root = Path(tmp) / "injected"
            result = runner.execute_workloads(settings, root, case_ids=[IDS[0]], mode="injected",
                                             conditions=["clean", "wrapped"], selection="first", workers=1)
            self.assertTrue(result["execution_complete"])
            clean, wrapped = [root / "w" / ("j%02d-t00" % i) for i in range(2)]
            for workspace in (clean, wrapped):
                self.assertFalse((workspace / "materials").exists())
                self.assertFalse((workspace / "normalize_order.py").exists())
            task = load_case(IDS[0]).tasks[0]
            self.assertNotIn(task["task_id"], (clean / "docs/reference.md").read_text())
            self.assertIn(json.dumps(task, ensure_ascii=False, indent=2), (wrapped / "docs/reference.md").read_text())
            self.assertNotIn("write-page-chain", (wrapped / "docs/reference.md").read_text())
            self.assertEqual(inputs[0], inputs[1])
            self.assertNotIn(task["task_id"], json.dumps(inputs[0]))
            authorized = Path(tmp) / "authorized"
            runner.execute_workloads(settings, authorized, case_ids=[IDS[0]], selection="first", workers=1)
            self.assertIn(task["task_id"], inputs[2][1]["content"])
            self.assertFalse((authorized / "w/j00-t00/materials").exists())
            audit = audit_directory(authorized, regrade=True)
            self.assertTrue(audit["passed"], audit["errors"])


if __name__ == "__main__":
    unittest.main()
