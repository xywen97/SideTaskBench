"""File-backed task contracts, public/private boundaries and snapshot coverage."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.workloads.host_tasks import CASE_ROOT, load_host_tasks
from compute_bench.workloads.provider_atomic import catalog as atomic
from compute_bench.coding.environment import create_workspace
from compute_bench.coding.tasks import build_coding_cases
from compute_bench.coding.provenance import snapshot_sources, task_materials
from compute_bench.coding.audit import audit_directory
from tests.test_coding_audit import _fixture


class TaskMaterialTests(unittest.TestCase):
    def test_edits_to_host_files_are_authoritative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            shutil.copytree(CASE_ROOT, root)
            case = root / "coding-01"
            (case / "instructions.md").write_text("Changed user request.\n")
            (case / "reference/reference.md").write_text("Changed reference.\n")
            (case / "materials/solution.py").write_text("def changed(): pass\n")
            loaded = load_host_tasks(root)[0]
            self.assertEqual(loaded["user_task"], "Changed user request.")
            self.assertEqual(loaded["reference_text"], "Changed reference.\n")
            self.assertEqual(loaded["repo_files"]["solution.py"], "def changed(): pass\n")

    def test_private_material_cannot_be_mapped_into_public_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            shutil.copytree(CASE_ROOT, root)
            path = root / "coding-01/task.json"
            metadata = json.loads(path.read_text())
            for source in ("private/solution.py", "materials/../private/solution.py", "/tmp/secret"):
                metadata["repo_files"]["solution.py"] = source
                path.write_text(json.dumps(metadata))
                with self.subTest(source=source), self.assertRaises(ValueError):
                    load_host_tasks(root)

    def test_material_symlink_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cases"
            shutil.copytree(CASE_ROOT, root)
            path = root / "coding-01/reference/reference.md"
            path.unlink()
            with self.assertRaises(ValueError):
                load_host_tasks(root)
            path.symlink_to(root / "coding-01/private/solution.py")
            with self.assertRaises(ValueError):
                load_host_tasks(root)

    def test_workspace_is_a_public_copy_and_does_not_modify_source_materials(self):
        before = task_materials()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
            create_workspace(case, workspace, "clean", "compatibility_v3")
            self.assertFalse((workspace / "private").exists())
            self.assertFalse((workspace / "task.json").exists())
            self.assertEqual((workspace / "solution.py").read_text(), case["repo_files"]["solution.py"])
            (workspace / "solution.py").write_text("# runtime edit\n")
        self.assertEqual(task_materials(), before)

    def test_atomic_private_files_are_loaded_but_not_needed_for_public_catalog(self):
        public = atomic.public_atomic_tasks()
        with tempfile.TemporaryDirectory() as tmp, patch.object(atomic, "PRIVATE_ROOT", Path(tmp)):
            self.assertEqual(atomic.public_atomic_tasks(), public)
            with self.assertRaises(ValueError):
                atomic.atomic_task_catalog()

    def test_snapshots_include_all_material_bytes_separately_from_runtime_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = snapshot_sources(root)
            expected = task_materials()
            self.assertEqual(set(metadata["task_material_sha256"]), set(expected))
            for path, data in expected.items():
                self.assertEqual((root / "task_materials" / path).read_bytes(), data)
            self.assertFalse(any("/cases/" in p or "/private/" in p for p in metadata["source_sha256"]))

    def test_tampered_material_snapshot_blocks_regrading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root)
            (root / "task_materials/workloads/host_tasks/cases/coding-01/reference/reference.md").write_text("changed")
            with patch("compute_bench.coding.audit.grade_main") as grade:
                audited = audit_directory(root, regrade=True)
            self.assertFalse(audited["passed"])
            self.assertIn("task_material_inventory", audited["errors"])
            grade.assert_not_called()
