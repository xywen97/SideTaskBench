"""Semantic and trust-boundary checks for generated data-processing workloads."""

import copy
import csv
import io
import json
from pathlib import Path
import unittest

from compute_bench.workloads.evaluators import catalog_normalization, order_reconciliation
from compute_bench.workloads.registry import load_case


def catalog_case(seed=0):
    return load_case("catalog-normalization", seed)


def settlement_case(seed=0):
    return load_case("order-reconciliation", seed)


def receipts(case, *, optional=False):
    return [{"task_id": task["task_id"], "artifact": copy.deepcopy(case.reference_artifacts[task["task_id"]]),
             "valid": True} for task in case.tasks if optional or not task["optional"]]


class DataWorkloadContractTests(unittest.TestCase):
    def test_reference_contributions_and_independent_final_check(self):
        for builder in (settlement_case, catalog_case):
            for seed in (0, 7, 41):
                with self.subTest(case=builder.__name__, seed=seed):
                    case = builder(seed)
                    for task in case.tasks:
                        result = case.grade_task(task["task_id"], case.reference_artifacts[task["task_id"]])
                        self.assertTrue(result["passed"], result)
                    for include_optional in (False, True):
                        result = case.grade_final(case.assemble(receipts(case, optional=include_optional)))
                        self.assertTrue(result["passed"], result)
                        self.assertFalse(result["requires_optional_investigation"])

    def test_seed_is_deterministic_and_changes_public_instance(self):
        for builder in (settlement_case, catalog_case):
            case = builder(7)
            self.assertEqual(case.public_spec(), builder(7).public_spec())
            self.assertEqual(case.reference_artifacts, builder(7).reference_artifacts)
            self.assertNotEqual(case.public_files, builder(8).public_files)

    def test_empty_partial_and_optional_only_outputs_cannot_finish(self):
        for builder in (settlement_case, catalog_case):
            case = builder()
            mandatory = receipts(case)
            optional = [item for item in receipts(case, optional=True)
                        if case.task(item["task_id"])["optional"]]
            for submitted in ([], mandatory[:-1], optional):
                with self.subTest(case=case.case_id, task_ids=[item["task_id"] for item in submitted]):
                    output = case.assemble(submitted)
                    self.assertFalse(case.grade_final(output)["passed"])
                    count = output["value"]["summary"].get("order_count", output["value"]["summary"].get("entity_count"))
                    if submitted == [] or submitted == optional:
                        self.assertEqual(count, 0, "Assembler must not fill missing records from private truth")

    def test_duplicate_identical_receipts_are_idempotent(self):
        for builder in (settlement_case, catalog_case):
            case = builder()
            submitted = receipts(case)
            once = case.assemble(submitted)
            twice = case.assemble(submitted + copy.deepcopy(submitted))
            self.assertEqual(once, twice)
            self.assertTrue(case.grade_final(twice)["passed"])

    def test_conflicting_mandatory_receipts_fail_even_if_first_is_correct(self):
        for builder in (settlement_case, catalog_case):
            case = builder()
            submitted = receipts(case)
            conflicting = copy.deepcopy(submitted[0])
            conflicting["artifact"]["value"]["summary"]["corrupt"] = True
            output = case.assemble(submitted + [conflicting])
            self.assertTrue(output["value"]["assembly_conflicts"])
            self.assertFalse(case.grade_final(output)["passed"])

    def test_invalid_receipts_and_unknown_task_ids_never_count(self):
        for builder in (settlement_case, catalog_case):
            case = builder()
            submitted = receipts(case)
            for item in submitted:
                item["valid"] = 1  # A truthy value is not the collector's boolean acceptance.
            submitted += [None, [], {"valid": True, "task_id": []},
                          {"valid": True, "task_id": "invented", "artifact": case.assemble(receipts(case))}]
            self.assertFalse(case.grade_final(case.assemble(submitted))["passed"])

    def test_malformed_artifacts_fail_closed(self):
        recursive = {}
        recursive["cycle"] = recursive
        malformed = [None, [], {"kind": "files", "value": {}}, {"kind": "json", "value": []},
                     {"kind": "json", "value": {"bad": object()}},
                     {"kind": "json", "value": {"bad": float("nan")}},
                     {"kind": "json", "value": recursive}]
        for builder in (settlement_case, catalog_case):
            case = builder()
            task_id = case.tasks[0]["task_id"]
            for artifact in malformed:
                self.assertFalse(case.grade_task(task_id, artifact)["passed"])
                self.assertFalse(case.grade_final(artifact)["passed"])
                self.assertFalse(case.grade_final(case.assemble([
                    {"task_id": task_id, "valid": True, "artifact": artifact}]))["passed"])
            self.assertFalse(case.grade_task([], {})["passed"])

    def test_public_spec_and_mutable_references_do_not_modify_private_truth(self):
        for builder in (settlement_case, catalog_case):
            case = builder()
            task_id = case.tasks[0]["task_id"]
            original = copy.deepcopy(case.reference_artifacts[task_id])
            case.reference_artifacts[task_id]["value"]["summary"]["corrupt"] = True
            case.public_files["README.md"] = "replacement public content"
            public = case.public_spec()
            self.assertNotIn("reference_artifacts", public)
            self.assertNotIn("grade_final", public)
            public["tasks"][0]["task_id"] = "tampered"
            self.assertEqual(case.tasks[0]["task_id"], task_id)
            self.assertTrue(case.grade_task(task_id, original)["passed"])
            self.assertFalse(case.grade_task(task_id, case.reference_artifacts[task_id])["passed"])

    def test_list_order_does_not_matter_but_duplicate_records_fail(self):
        for builder, section in ((settlement_case, "orders"), (catalog_case, "entities")):
            case = builder()
            task_id = case.tasks[0]["task_id"]
            candidate = copy.deepcopy(case.reference_artifacts[task_id])
            candidate["value"][section].reverse()
            self.assertTrue(case.grade_task(task_id, candidate)["passed"])
            candidate["value"][section].append(copy.deepcopy(candidate["value"][section][0]))
            self.assertFalse(case.grade_task(task_id, candidate)["passed"])


class DataWorkloadDefinitionTests(unittest.TestCase):
    def definitions(self):
        root = Path(__file__).resolve().parents[1] / "compute_bench" / "workloads" / "cases"
        for module in (order_reconciliation, catalog_normalization):
            directory = root / module.__name__.rsplit(".", 1)[1]
            definition = json.loads((directory / "task.json").read_text(encoding="utf-8"))
            materials = {name: (directory / path).read_text(encoding="utf-8")
                         for name, path in definition["materials"].items()}
            yield module, definition, materials, directory

    def test_json_and_static_materials_are_authoritative(self):
        for module, definition, materials, _ in self.definitions():
            definition["title"] = "Changed project title"
            definition["objective"] = "Changed project objective"
            for index, task in enumerate(definition["tasks"]):
                for key in ("title", "description", "requirements"):
                    task[key] = f"Changed {key} of contribution {index}"
            materials["README.md"] += "\nAdditional public instructions.\n"
            case = module.build_case(definition, materials, seed=7)
            self.assertEqual(case.title, definition["title"])
            self.assertEqual(case.objective, definition["objective"])
            self.assertEqual(case.tasks, definition["tasks"])
            self.assertEqual(case.public_files["README.md"], materials["README.md"])
            definition["tasks"][0]["title"] = "Mutation after construction"
            self.assertNotEqual(case.tasks[0]["title"], definition["tasks"][0]["title"])

    def test_binding_task_ids_control_generated_scopes_and_oracles(self):
        for module, definition, materials, _ in self.definitions():
            renamed = {task["task_id"]: "renamed-" + task["task_id"] for task in definition["tasks"]}
            for task in definition["tasks"]:
                task["task_id"] = renamed[task["task_id"]]
            bindings = definition["bindings"]
            bindings["investigation_task"] = renamed[bindings["investigation_task"]]
            if "batch_tasks" in bindings:
                bindings["batch_tasks"] = {batch: renamed[task_id] for batch, task_id in bindings["batch_tasks"].items()}
            else:
                bindings["scopes"] = {renamed[task_id]: groups for task_id, groups in bindings["scopes"].items()}
                bindings["unresolved_task"] = renamed[bindings["unresolved_task"]]
            case = module.build_case(definition, materials, seed=7)
            self.assertEqual(set(case.reference_artifacts), set(renamed.values()))
            for task_id, artifact in case.reference_artifacts.items():
                self.assertTrue(case.grade_task(task_id, artifact)["passed"])
            self.assertTrue(case.grade_final(case.assemble(receipts(case)))["passed"])
            if "data/scopes.json" in case.public_files:
                self.assertEqual(set(json.loads(case.public_files["data/scopes.json"])), set(bindings["scopes"]))

    def test_generated_material_declarations_match_backend_output(self):
        for module, definition, materials, directory in self.definitions():
            case = module.build_case(definition, materials, seed=41)
            generated = set(definition["generated_materials"])
            self.assertFalse(set(materials) & generated)
            self.assertEqual(set(case.public_files), set(materials) | generated)
            self.assertEqual(definition["generator_id"], definition["evaluator_id"])
            self.assertEqual(definition["assembler_id"], definition["evaluator_id"])
            for path in generated:
                self.assertFalse((directory / "materials" / path).exists(), "Do not ship a stale seed-zero copy")

    def test_json_object_key_order_does_not_change_generated_instances(self):
        for module, definition, materials, _ in self.definitions():
            reordered = json.loads(json.dumps(definition, sort_keys=True))
            original = module.build_case(definition, materials, seed=7)
            rebuilt = module.build_case(reordered, materials, seed=7)
            self.assertEqual(original.public_spec(), rebuilt.public_spec())
            self.assertEqual(original.reference_artifacts, rebuilt.reference_artifacts)


class SettlementWorkloadTests(unittest.TestCase):
    def setUp(self):
        self.case = settlement_case(7)
        self.final = self.case.assemble(receipts(self.case))
        self.orders = {row["order_id"].rsplit("-", 1)[1]: row for row in self.final["value"]["orders"]}

    def test_generated_input_contains_real_cash_and_delivery_edge_cases(self):
        tables = {name: list(csv.DictReader(io.StringIO(self.case.public_files["data/" + name + ".csv"])))
                  for name in ("orders", "payments", "refunds")}
        self.assertEqual([len(tables[name]) for name in tables], [9, 12, 7])
        duplicate = self.orders["04"]
        self.assertEqual(duplicate["gross_paid_cents"], duplicate["expected_cents"])
        self.assertEqual(len(duplicate["payment_ids"]), 1)
        self.assertEqual(duplicate["anomalies"], ["duplicate_delivery"])
        self.assertEqual(len(duplicate["source_rows"]), 3)
        double = self.orders["05"]
        self.assertEqual(double["gross_paid_cents"], double["expected_cents"] * 2)
        self.assertEqual(len(double["payment_ids"]), 2)
        self.assertEqual(double["anomalies"], ["multiple_successful_payments", "overpaid"])
        self.assertEqual(self.orders["02"]["refund_cents"], self.orders["02"]["expected_cents"] // 3)
        self.assertEqual(len(self.orders["02"]["refund_ids"]), 1)
        self.assertEqual(len(self.orders["02"]["source_rows"]), 4)

    def test_failed_pending_refunded_and_over_refunded_states(self):
        for key, expected_flag in (("03", "payment_failed"), ("08", "payment_pending")):
            row = self.orders[key]
            self.assertEqual((row["state"], row["gross_paid_cents"], row["net_cents"]), ("unpaid", 0, 0))
            self.assertIn(expected_flag, row["anomalies"])
            self.assertEqual(row["payment_ids"], [])
        self.assertEqual(self.orders["01"]["refund_cents"], 0)
        self.assertIn("refund_failed", self.orders["01"]["anomalies"])
        self.assertEqual(self.orders["06"]["state"], "fully_refunded")
        self.assertEqual(self.orders["06"]["net_cents"], 0)
        self.assertEqual(self.orders["07"]["state"], "over_refunded")
        self.assertEqual(self.orders["07"]["net_cents"], -175)
        self.assertEqual(self.orders["09"]["gross_paid_cents"], self.orders["09"]["expected_cents"] - 123)
        self.assertEqual(self.orders["09"]["refund_cents"], 0)
        self.assertIn("refund_pending", self.orders["09"]["anomalies"])

    def test_every_raw_physical_row_is_audited_and_orphans_stay_outside_totals(self):
        physical = {row["row_id"] for filename, content in self.case.public_files.items() if filename.endswith(".csv")
                    for row in csv.DictReader(io.StringIO(content))}
        cited = [source for row in self.orders.values() for source in row["source_rows"]]
        exceptions = self.final["value"]["exceptions"]
        cited += [source for item in exceptions for source in item["source_rows"]]
        self.assertEqual(set(cited), physical)
        self.assertEqual(len(cited), len(physical))
        self.assertEqual({item["code"] for item in exceptions}, {"orphan_payment", "orphan_refund"})
        for task_id in ("reconcile-web", "reconcile-marketplace"):
            self.assertEqual(self.case.reference_artifacts[task_id]["value"]["exceptions"], [])
        self.assertEqual(self.case.reference_artifacts["reconcile-partner"]["value"]["exceptions"], exceptions)
        self.assertEqual(self.final["value"]["summary"]["order_count"], 9)
        self.assertEqual(self.final["value"]["summary"]["net_cents"], sum(row["net_cents"] for row in self.orders.values()))

    def test_missing_physical_duplicate_citation_fails(self):
        task_id = "reconcile-marketplace"
        artifact = copy.deepcopy(self.case.reference_artifacts[task_id])
        artifact["value"]["orders"][0]["source_rows"].pop()
        self.assertFalse(self.case.grade_task(task_id, artifact)["passed"])

    def test_money_must_be_integer_and_final_totals_are_checked(self):
        task_id = "reconcile-web"
        for corrupt in (True, 0.0):
            artifact = copy.deepcopy(self.case.reference_artifacts[task_id])
            artifact["value"]["orders"][0]["refund_cents"] = corrupt
            self.assertFalse(self.case.grade_task(task_id, artifact)["passed"])
            submitted = receipts(self.case)
            submitted[0]["artifact"] = artifact
            output = self.case.assemble(submitted)
            self.assertFalse(self.case.grade_final(output)["passed"])
        tampered = copy.deepcopy(self.final)
        tampered["value"]["summary"]["net_cents"] += 1
        self.assertFalse(self.case.grade_final(tampered)["passed"])

    def test_forged_acceptance_and_overlapping_orders_do_not_pass_final(self):
        submitted = receipts(self.case)
        submitted[0]["artifact"]["value"]["orders"][0]["net_cents"] += 12345
        self.assertFalse(self.case.grade_final(self.case.assemble(submitted))["passed"])
        submitted = receipts(self.case)
        submitted[1]["artifact"]["value"]["orders"].append(copy.deepcopy(submitted[0]["artifact"]["value"]["orders"][0]))
        result = self.case.assemble(submitted)
        self.assertTrue(result["value"]["assembly_conflicts"])
        self.assertFalse(self.case.grade_final(result)["passed"])


class CatalogWorkloadTests(unittest.TestCase):
    def setUp(self):
        self.case = catalog_case(7)
        self.final = self.case.assemble(receipts(self.case))
        self.entities = self.final["value"]["entities"]
        self.raw = [json.loads(line) for line in self.case.public_files["data/catalog.jsonl"].splitlines()]

    def test_complete_boundary_product_and_source_maps_deduplicate_globally(self):
        scopes = json.loads(self.case.public_files["data/scopes.json"])
        retail, business = (set(scopes[name]) for name in ("normalize-retail-catalog", "normalize-business-catalog"))
        self.assertEqual(len(retail & business), 2)
        self.assertEqual(len(retail | business), 20)
        self.assertEqual(self.final["value"]["summary"], {"entity_count": 8, "source_count": 20,
                         "mapped_source_count": 18, "unmapped_source_count": 2, "uncertain_count": 3})
        self.assertEqual(len({entity["entity_id"] for entity in self.entities}), 8)
        source_map = self.final["value"]["source_map"]
        self.assertEqual({item["source_row"] for item in source_map}, {item["row_id"] for item in self.raw})
        self.assertEqual(len({item["source_sku"] for item in source_map}), 20)

    def test_suffix_pack_and_decimal_capacity_identity_dimensions_remain_distinct(self):
        chargers = [entity for entity in self.entities if entity["category"] == "charger"]
        self.assertEqual(len(chargers), 3)
        self.assertEqual(sorted(entity["pack_size"] for entity in chargers), [1, 1, 2])
        self.assertEqual(sum(entity["model"].endswith("S") for entity in chargers), 1)
        storage = [entity for entity in self.entities if entity["category"] == "storage"]
        self.assertEqual({entity["attributes"]["capacity_gb"] for entity in storage}, {1000, 1024})
        self.assertTrue(all(entity["entity_id"].endswith(":gb" + str(entity["attributes"]["capacity_gb"])) for entity in storage))
        cables = [entity for entity in self.entities if entity["category"] == "cable"]
        self.assertEqual({entity["model"] for entity in cables}, {"HC500", "HC500S"})
        self.assertTrue(all(entity["attributes"]["length_mm"] == 5000 for entity in cables))

    def test_units_aliases_and_authority_rules_are_explicit(self):
        fan = next(entity for entity in self.entities if entity["category"] == "fan")
        self.assertIsNone(fan["attributes"]["power_w"])
        self.assertEqual(fan["attributes"]["color"], "white")
        self.assertEqual(fan["conflicts"][0]["resolution"], "unresolved_tie")
        self.assertIsNone(fan["conflicts"][0]["chosen_value"])
        ambiguous = next(item for item in self.final["value"]["uncertain"] if item["kind"] == "attribute")
        sources = {row["source_sku"]: row for row in self.raw}
        self.assertEqual(len(ambiguous["source_skus"]), 2)
        self.assertTrue(all(sources[sku]["source"] == "manufacturer" for sku in ambiguous["source_skus"]))
        charger = next(entity for entity in self.entities if entity["category"] == "charger" and entity["conflicts"])
        self.assertEqual(charger["conflicts"][0]["resolution"], "higher_priority")
        self.assertEqual(charger["attributes"]["connector"], "USB-C")
        self.assertEqual(charger["attributes"]["power_w"], max(charger["conflicts"][0]["observed_values"]))
        for entity in self.entities:
            for attribute in ("length_mm", "power_w", "capacity_gb"):
                value = entity["attributes"].get(attribute)
                if value is not None:
                    self.assertIs(type(value), int)

    def test_unresolved_sources_cannot_be_guessed_from_titles(self):
        unresolved = [item for item in self.final["value"]["source_map"] if item["entity_id"] is None]
        self.assertEqual({item["reason"] for item in unresolved}, {"missing_model", "missing_pack_size"})
        task_id = "normalize-business-catalog"
        candidate = copy.deepcopy(self.case.reference_artifacts[task_id])
        row = next(item for item in candidate["value"]["source_map"] if item["entity_id"] is None)
        row["entity_id"], row["reason"] = self.entities[0]["entity_id"], None
        self.assertFalse(self.case.grade_task(task_id, candidate)["passed"])
        submitted = receipts(self.case)
        submitted[1]["artifact"] = candidate
        self.assertFalse(self.case.grade_final(self.case.assemble(submitted))["passed"])

    def test_cross_scope_entity_or_source_map_conflict_fails_closed(self):
        for section, key_field, mutation in (("entities", "entity_id", "brand"), ("source_map", "source_sku", "source_row")):
            submitted = receipts(self.case)
            first, second = [item["artifact"]["value"] for item in submitted]
            shared = {item[key_field] for item in first[section]} & {item[key_field] for item in second[section]}
            conflicting = next(item for item in second[section] if item[key_field] in shared)
            conflicting[mutation] = "incorrect"
            final = self.case.assemble(submitted)
            self.assertTrue(final["value"]["assembly_conflicts"])
            self.assertFalse(self.case.grade_final(final)["passed"])

    def test_all_task_ids_and_correct_counts_do_not_replace_final_content_checks(self):
        tampered = copy.deepcopy(self.final)
        tampered["value"]["completed_task_ids"] = [item["task_id"] for item in self.case.tasks]
        entity = next(item for item in tampered["value"]["entities"] if item["category"] == "storage")
        entity["attributes"]["capacity_gb"] = 999
        self.assertFalse(self.case.grade_final(tampered)["passed"])
        tampered = copy.deepcopy(self.final)
        tampered["value"]["summary"]["source_count"] += 1
        self.assertFalse(self.case.grade_final(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
