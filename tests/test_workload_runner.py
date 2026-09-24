"""Transport/assembly integration with an explicitly fake model, no paid calls."""

import contextlib
import io
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.cli import main
from compute_bench.workloads.contracts import checked_relative, write_files
from compute_bench.workloads.definitions import case_definition
from compute_bench.workloads.provenance import current_resource_hashes
from compute_bench.workloads.registry import load_case
from compute_bench.workloads.runner import execute_workloads
from microcoder.config import Settings


class WorkloadRunnerTests(unittest.TestCase):
    def test_paths_fail_closed(self):
        for path in ("", ".", "..", "x/../a", "/tmp/a", "x//a", "x/", ".env", "x/.env.local", ".git/config", "x\\a"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                checked_relative(path)
        self.assertEqual(checked_relative("repo/report.py"), "repo/report.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "link").symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                write_files(root, {"link/report.py": "text"})

    def test_cli_exports_only_public_materials(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "case"
            main(["workloads", "export", "api-migration", str(root), "--seed", "7"])
            spec = json.loads((root / "case.json").read_text())
            self.assertNotIn("reference_artifacts", spec)
            self.assertNotIn("grade_task", spec)
            request = json.loads((root / "request.json").read_text())
            self.assertEqual(request["components"], spec["tasks"])
            self.assertEqual((root / "materials/repo/order_report.py").read_text(), spec["public_files"]["repo/order_report.py"])

    def test_cli_definition_does_not_invoke_evaluator_or_generate_inputs(self):
        with contextlib.redirect_stdout(io.StringIO()) as output, patch(
                "compute_bench.workloads.cli.load_case", side_effect=AssertionError("Definition display needs no backend")):
            main(["workloads", "show", "order-reconciliation", "--definition"])
        definition = json.loads(output.getvalue())
        self.assertEqual(definition, case_definition("order-reconciliation"))
        self.assertTrue(definition["generated_materials"])
        self.assertNotIn("public_files", definition)

    def test_cli_seeded_export_materializes_generated_inputs(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "case"
            main(["workloads", "export", "order-reconciliation", str(root), "--seed", "7"])
            expected = load_case("order-reconciliation", seed=7).public_spec()
            self.assertEqual(json.loads((root / "case.json").read_text()), expected)
            inventory = {p.relative_to(root / "materials").as_posix(): p.read_bytes().decode("utf-8")
                         for p in (root / "materials").rglob("*") if p.is_file()}
            self.assertEqual(inventory, expected["public_files"])
            self.assertEqual({p.name for p in root.iterdir()}, {"case.json", "request.json", "materials"})

    def test_real_http_roundtrip_with_fixture_model_and_no_gold_backfill(self):
        case = load_case("order-reconciliation")
        task = case.tasks[0]
        artifact = case.reference_artifacts[task["task_id"]]
        payload = json.dumps({"task_id": task["task_id"], "artifact": artifact})
        command = ("printf %s " + shlex.quote(payload) + " > payload.json && "
                   "curl -sS --unix-socket /workspace/.collector.sock -H 'Content-Type: application/json' "
                   "--data-binary @payload.json http://collector/submit")

        class FixtureClient:
            def __init__(self, settings):
                self.calls = 0

            def complete(self, messages, tools):
                self.calls += 1
                metadata = {"response_id": "fixture-only-" + str(self.calls), "usage": {"total_tokens": 0}}
                if self.calls == 1:
                    return {"role": "assistant", "content": "", "tool_calls": [
                        {"id": "fixture-submit", "type": "function", "function": {
                            "name": "shell", "arguments": json.dumps({"command": command})}}]}, metadata
                return {"role": "assistant", "content": "Fixture delivery complete."}, metadata

            def close(self):
                pass

        with tempfile.TemporaryDirectory(prefix="wl-test-") as tmp, patch(
                "compute_bench.workloads.runner.ChatClient", FixtureClient), contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "run"
            result = execute_workloads(Settings(api_key="test-only"), root,
                                       case_ids=[case.case_id], selection="first", workers=1)
            self.assertEqual(result["valid_deliveries"], 1)
            self.assertEqual(result["large_tasks_complete"], 0)
            self.assertEqual(result["mode"], "authorized")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["workload_definition_version"], 1)
            self.assertEqual(manifest["workload_resource_sha256"],
                             current_resource_hashes(manifest["workload_resource_case_ids"]))
            aggregate = json.loads((root / "jobs/order-reconciliation-authorized/result.json").read_text())
            self.assertFalse(aggregate["large_task_complete"])
            self.assertEqual(aggregate["completed_tasks"], 1)
            self.assertEqual(aggregate["total_tasks"], 4)
            self.assertFalse(any("gold" in p.name or "acceptance" in p.name for p in (root / "w").rglob("*")))
            with self.assertRaises(ValueError):
                execute_workloads(Settings(api_key="test-only"), root, case_ids=[case.case_id])

    def test_reject_socket_path_before_api(self):
        with tempfile.TemporaryDirectory() as tmp, patch("compute_bench.workloads.runner.ChatClient") as client:
            with self.assertRaisesRegex(ValueError, "socket"):
                execute_workloads(Settings(api_key="test-only"), Path(tmp) / ("a" * 100),
                                  case_ids=["api-migration"])
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
