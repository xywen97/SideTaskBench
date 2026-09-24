"""Declarative-case loading and trusted-backend contract boundaries; no model calls."""

import copy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from compute_bench.workloads import definitions, registry
from compute_bench.workloads.contracts import WorkloadCase


SOURCE_ROOT = Path(definitions.CASE_ROOT)


class WorkloadDefinitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workload-definitions-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / "cases"
        self.case_dir = self.root / "fixture"
        shutil.copytree(SOURCE_ROOT / "order_reconciliation", self.case_dir)
        self.path = self.case_dir / "task.json"
        self.original = json.loads(self.path.read_text(encoding="utf-8"))
        self.case_id = self.original["case_id"]
        patcher = patch.object(definitions, "CASE_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, definition=None):
        self.path.write_text(json.dumps(self.original if definition is None else definition), encoding="utf-8")

    def test_edits_to_json_and_referenced_material_are_loaded_without_python_edits(self):
        before = registry.load_case(self.case_id)
        edited = copy.deepcopy(self.original)
        edited.update(title="Reviewed title", objective="Reviewed objective")
        edited["tasks"][0].update(title="Reviewed contribution", description="Revised task instructions",
                                  requirements="Revised required behavior")
        edited["materials"]["README.md"] = "materials/review.txt"
        text = "Public specification revision.\r\nExact newlines survive loading.\n"
        (self.case_dir / "materials/review.txt").write_bytes(text.encode("utf-8"))
        self.write(edited)
        after = registry.load_case(self.case_id)
        self.assertNotEqual(before.title, after.title)
        self.assertEqual(after.title, edited["title"])
        self.assertEqual(after.objective, edited["objective"])
        self.assertEqual(after.tasks, edited["tasks"])
        self.assertEqual(after.public_files["README.md"], text)
        self.assertEqual(definitions.case_definition(self.case_id), edited)

    def test_new_json_case_is_discovered_and_reuses_registered_backend(self):
        clone = self.root / "new_json_only_case"
        shutil.copytree(self.case_dir, clone)
        value = copy.deepcopy(self.original)
        value.update(case_id="new-reconciliation", case_number=1, title="New JSON-only workload")
        (clone / "task.json").write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(list(definitions.available_definitions()), [value["case_id"], self.case_id])
        self.assertNotIn(value["case_id"], registry.BACKENDS)
        case = registry.load_case(value["case_id"], seed=7)
        self.assertEqual((case.case_id, case.title, case.tasks), (value["case_id"], value["title"], value["tasks"]))

    def test_discovery_rejects_duplicate_case_ids_and_empty_catalog(self):
        shutil.copytree(self.case_dir, self.root / "duplicate")
        with self.assertRaisesRegex(ValueError, "Repeated case_id"):
            definitions.available_definitions()
        with patch.object(definitions, "CASE_ROOT", self.directory / "empty"), self.assertRaises(ValueError):
            definitions.available_definitions()

    def test_unknown_backends_and_mismatched_capabilities_are_rejected_before_import(self):
        for field in ("evaluator_id", "assembler_id", "generator_id"):
            value = copy.deepcopy(self.original)
            value[field] = "unregistered-backend-v1"
            self.write(value)
            with self.subTest(field=field), patch.object(registry.importlib, "import_module") as importer:
                with self.assertRaises(ValueError):
                    registry.load_case(self.case_id)
                importer.assert_not_called()

    def test_duplicate_json_fields_are_rejected_at_any_nesting_depth(self):
        raw = json.dumps(self.original)
        duplicates = [raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1),
                      raw.replace('"bindings": {', '"bindings": {"probe": 1, "probe": 2,', 1)]
        for content in duplicates:
            self.path.write_text(content, encoding="utf-8")
            with self.subTest(content=content[:50]), self.assertRaisesRegex(ValueError, "Repeated JSON field"):
                definitions.load_definition(self.case_id)

    def test_nonfinite_json_numbers_are_rejected_in_nested_parameters(self):
        value = copy.deepcopy(self.original)
        value["parameters"] = {"sentinel": 1}
        raw = json.dumps(value)
        for literal in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            self.path.write_text(raw.replace('"sentinel": 1', '"sentinel": ' + literal), encoding="utf-8")
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                definitions.load_definition(self.case_id)

    def test_schema_and_public_task_type_errors_are_rejected(self):
        changes = [lambda d: d.pop("title"), lambda d: d.update(unrecognized=True),
                   lambda d: d.update(schema_version=True), lambda d: d.update(case_number=True),
                   lambda d: d.update(tasks=[]), lambda d: d["tasks"].append(copy.deepcopy(d["tasks"][0])),
                   lambda d: d["tasks"][0].update(optional=1), lambda d: d["tasks"][0].update(title=7),
                   lambda d: d["tasks"][0].update(artifact_kind="executable"),
                   lambda d: d["tasks"][0].update(description="")]
        for index, change in enumerate(changes):
            value = copy.deepcopy(self.original)
            change(value)
            self.write(value)
            with self.subTest(change=index), self.assertRaises(ValueError):
                definitions.load_definition(self.case_id)

    def test_material_paths_cannot_escape_or_target_private_locations(self):
        mappings = [{"../escape.txt": "materials/README.md"}, {"/tmp/escape.txt": "materials/README.md"},
                    {".env": "materials/README.md"}, {"README.md": "../README.md"},
                    {"README.md": "materials/../../README.md"}, {"README.md": "elsewhere/README.md"},
                    {"README.md": "materials\\README.md"}]
        for mapping in mappings:
            value = copy.deepcopy(self.original)
            value["materials"] = mapping
            self.write(value)
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                definitions.load_definition(self.case_id)
        value = copy.deepcopy(self.original)
        value["generated_materials"].append("../outside.json")
        self.write(value)
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)

    def test_task_definition_symlink_is_rejected(self):
        original = self.case_dir / "original.json"
        self.path.rename(original)
        self.path.symlink_to(original)
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)

    def test_material_symlink_and_symlinked_ancestor_are_rejected(self):
        material = self.case_dir / "materials/README.md"
        material.rename(self.directory / "external-readme")
        material.symlink_to(self.directory / "external-readme")
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)
        material.unlink()
        (self.directory / "external-readme").rename(material)
        (self.case_dir / "materials").rename(self.directory / "external-materials")
        (self.case_dir / "materials").symlink_to(self.directory / "external-materials", target_is_directory=True)
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)

    def test_case_directory_symlink_is_rejected(self):
        external = self.directory / "external-case"
        self.case_dir.rename(external)
        self.case_dir.symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)

    def test_missing_or_nonregular_material_is_rejected(self):
        material = self.case_dir / "materials/README.md"
        material.unlink()
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)
        material.mkdir()
        with self.assertRaises(ValueError):
            definitions.load_definition(self.case_id)

    def test_material_inventory_rejects_overlap_prefix_conflicts_and_undeclared_references(self):
        changes = [lambda d: d["generated_materials"].append("README.md"),
                   lambda d: d["generated_materials"].append(d["generated_materials"][0]),
                   lambda d: d["materials"].update({"data": "materials/README.md"}),
                   lambda d: d["generated_materials"].append("data/orders.csv/child"),
                   lambda d: d["tasks"][0]["material_paths"].append("not-declared.txt"),
                   lambda d: d["tasks"][0].update(material_paths="README.md"),
                   lambda d: d.update(materials={}, generated_materials=[], generator_id=None),
                   lambda d: d.update(generator_id=None), lambda d: d.update(generated_materials=[])]
        for index, change in enumerate(changes):
            value = copy.deepcopy(self.original)
            change(value)
            self.write(value)
            with self.subTest(change=index), self.assertRaises(ValueError):
                definitions.load_definition(self.case_id)

    def test_only_declared_static_files_are_loaded_and_snapshotted(self):
        (self.case_dir / "materials/ignored-private.txt").write_text("Do not export this file.", encoding="utf-8")
        value, materials = definitions.load_definition(self.case_id)
        self.assertEqual(set(materials), set(value["materials"]))
        resources = definitions.case_resources(self.case_id)
        self.assertEqual(set(resources), {"fixture/task.json", "fixture/materials/README.md"})
        self.assertEqual(resources["fixture/task.json"], self.path.read_bytes())
        value["tasks"][0]["description"] = "caller mutation"
        self.assertNotEqual(value, definitions.case_definition(self.case_id))

    @staticmethod
    def backend_case(definition, materials, seed=0):
        return WorkloadCase(case_id=definition["case_id"], title=definition["title"], objective=definition["objective"],
                            tasks=copy.deepcopy(definition["tasks"]),
                            public_files={**materials, **{path: "generated\n" for path in definition["generated_materials"]}},
                            reference_artifacts={}, grade_task=lambda *args: {}, assemble=lambda *args: {},
                            grade_final=lambda *args: {})

    def reject_backend(self, backend):
        with patch.object(registry.importlib, "import_module", return_value=SimpleNamespace(build_case=backend)):
            with self.assertRaises(ValueError):
                registry.load_case(self.case_id)

    def test_backend_cannot_override_json_metadata_or_task_specs(self):
        for field, value in (("case_id", "wrong-case"), ("title", "wrong title"), ("objective", "wrong objective")):
            with self.subTest(field=field):
                self.reject_backend(lambda d, m, seed=0: replace(self.backend_case(d, m, seed), **{field: value}))

        def override_tasks(definition, materials, seed=0):
            case = self.backend_case(definition, materials, seed)
            case.tasks[0]["description"] = "Backend-supplied alternative instructions"
            return case

        self.reject_backend(override_tasks)

    def test_backend_input_mutation_cannot_redefine_the_comparison_contract(self):
        mutations = [lambda d: d.update(title="Changed inside backend"),
                     lambda d: d["tasks"][0].update(description="Changed inside backend"),
                     lambda d: d["generated_materials"].append("undeclared.txt")]
        for index, mutate in enumerate(mutations):
            def backend(definition, materials, seed=0):
                mutate(definition)
                return self.backend_case(definition, materials, seed)

            with self.subTest(mutation=index):
                self.reject_backend(backend)

    def test_backend_cannot_replace_static_content_or_generated_inventory(self):
        changes = [lambda files: files.update({"README.md": "Overwritten static instructions"}),
                   lambda files: files.pop("data/orders.csv"),
                   lambda files: files.update({"not-declared.txt": "extra output"}),
                   lambda files: files.update({"data/orders.csv": b"not text"})]
        for index, change in enumerate(changes):
            def backend(definition, materials, seed=0):
                case = self.backend_case(definition, materials, seed)
                change(case.public_files)
                return case

            with self.subTest(change=index):
                self.reject_backend(backend)

        def mutate_material_input(definition, materials, seed=0):
            materials["README.md"] = "Overwritten backend input"
            return self.backend_case(definition, materials, seed)

        self.reject_backend(mutate_material_input)
        self.reject_backend(lambda *args, **kwargs: {})


if __name__ == "__main__":
    unittest.main()
