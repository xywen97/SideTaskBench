"""The compact harness starts coding trials without loading the archived track."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.cli import main
from compute_bench.coding.runner import resume_coding
from compute_bench.coding.report import write_report
from microcoder.config import Settings


class BenchmarkEntrypointTests(unittest.TestCase):
    def test_dry_run_validates_full_and_selected_plans_without_credentials(self):
        for arguments, expected in (([], (750, 6000)),
                                    (["--host-task-ids", "coding-03", "coding-01",
                                      "--atomic-task-ids", "regression-empty-page"], (2, 16))):
            with self.subTest(arguments=arguments), \
                 patch("compute_bench.coding.cli.Settings.load") as settings, \
                 patch("compute_bench.coding.runner.execute_coding") as execute, \
                 redirect_stdout(io.StringIO()) as output:
                main(["run", "--dry-run", *arguments])
                result = json.loads(output.getvalue())
                self.assertEqual((result["pair_count"], result["planned_runs"]), expected)
                self.assertEqual(result["conditions"], ["wrapped"])
                self.assertEqual(result["repeats"], 8)
                settings.assert_not_called()
                execute.assert_not_called()

    def test_mainline_loads_without_archived_experiments_or_compatibility_modules(self):
        code = '''
import importlib, importlib.abc, sys
class RejectArchivedModules(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = {"compute_bench.agent", "compute_bench.config", "compute_bench.llm",
                     "compute_bench.experiment", "compute_bench.collector", "compute_bench.environment",
                     "compute_bench.scenarios", "compute_bench.scoring", "compute_bench.report",
                     "compute_bench.audit", "compute_bench.coding.collector", "compute_bench.coding.sandbox"}
        if fullname == "legacy" or fullname.startswith("legacy.") or fullname in forbidden:
            raise AssertionError("Mainline loaded retired module: " + fullname)
sys.meta_path.insert(0, RejectArchivedModules())
for name in ("compute_bench.cli", "compute_bench.coding.runner", "compute_bench.coding.audit",
             "compute_bench.coding.rescore", "compute_bench.coding.report"):
    importlib.import_module(name)
print("independent mainline")
'''
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "independent mainline")

    def test_default_and_compatibility_prefix_dispatch_identical_coding_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            args = ["run", "--output", str(output), "--host-task-ids", "coding-01", "coding-02", "--atomic-task-ids", "rewrite-user-record", "--conditions", "clean", "wrapped",
                    "--repeats", "1", "--workers", "1", "--max-steps", "12", "--label", "entry-test"]
            calls = []
            for prefix in ([], ["coding"]):
                with patch("compute_bench.coding.cli.Settings.load", return_value=Settings(api_key="synthetic")), \
                     patch("compute_bench.coding.runner.execute_coding", return_value={
                         "mechanism_demonstrated": False, "total_usage": {"total_tokens": 0},
                     }) as execute, redirect_stdout(io.StringIO()) as printed:
                    main(prefix + args)
                    calls.append(execute.call_args)
                    self.assertFalse(json.loads(printed.getvalue())["mechanism_demonstrated"])
            self.assertEqual(calls[0], calls[1])
            self.assertEqual(calls[0].kwargs["conditions"], ["clean", "wrapped"])
            self.assertEqual(calls[0].kwargs["host_task_ids"], ["coding-01", "coding-02"])
            self.assertEqual(calls[0].kwargs["atomic_task_ids"], ["rewrite-user-record"])
            self.assertEqual(calls[0].kwargs["max_steps"], 12)
            self.assertFalse(output.exists())

    def test_paired_flag_hands_the_runner_a_concrete_pair_list(self):
        # Regression: --paired once reached execute_coding as pairs=None, which
        # silently ran the full 25×30 cross product instead of the 8 pairs.
        from compute_bench.coding.pairing import HOST_TAILORED_PAIRS
        with tempfile.TemporaryDirectory() as directory, \
             patch("compute_bench.coding.cli.Settings.load", return_value=Settings(api_key="synthetic")), \
             patch("compute_bench.coding.runner.execute_coding", return_value={
                 "mechanism_demonstrated": False, "total_usage": {"total_tokens": 0},
             }) as execute, redirect_stdout(io.StringIO()):
            main(["run", "--paired", "--output", str(Path(directory) / "run"), "--repeats", "1"])
            pairs = execute.call_args.kwargs["pairs"]
            self.assertEqual([tuple(pair) for pair in pairs], list(HOST_TAILORED_PAIRS))
            self.assertIsNone(execute.call_args.kwargs["host_task_ids"])
            self.assertIsNone(execute.call_args.kwargs["atomic_task_ids"])

    def test_default_run_uses_unified_seventy_step_limit(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch("compute_bench.coding.cli.Settings.load", return_value=Settings(api_key="synthetic")), \
             patch("compute_bench.coding.runner.execute_coding", return_value={
                 "mechanism_demonstrated": False, "total_usage": {"total_tokens": 0},
             }) as execute, redirect_stdout(io.StringIO()):
            main(["run", "--output", str(Path(directory) / "run")])
            self.assertEqual(execute.call_args.kwargs["max_steps"], 70)

    def test_help_and_invalid_arguments_do_not_load_credentials_or_start_an_agent(self):
        for args, code in ((["--help"], 0), (["coding", "--help"], 0),
                           (["run", "--cases", "10"], 2), (["run", "--pairing-rotation", "1"], 2),
                           (["run", "--host-task-ids", "bad"], 2),
                           (["run", "--atomic-task-ids", "bad"], 2),
                           (["run", "--defenses", "egress"], 2),
                           (["run", "--host-task-ids", "coding-01", "coding-01"], 2), (["run", "--max-steps", "0"], 2)):
            with self.subTest(args=args), patch("compute_bench.coding.cli.Settings.load") as settings, \
                 patch("compute_bench.coding.runner.execute_coding") as execute, \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(args)
                self.assertEqual(raised.exception.code, code)
                settings.assert_not_called()
                execute.assert_not_called()

    def test_old_pending_layout_cannot_be_resumed_or_mutated_by_current_harness(self):
        for layout in (1, 2, 3, 4, 5):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                files = {"manifest.json": {"source_layout_version": layout},
                         "plan.json": [{"run_id": "pending"}], "cases.json": []}
                for name, value in files.items():
                    (root / name).write_text(json.dumps(value))
                before = {path.name: path.read_bytes() for path in root.iterdir()}
                with patch("compute_bench.coding.runner.Sandbox") as sandbox, \
                     patch("compute_bench.coding.runner.ChatClient") as client:
                    with self.assertRaisesRegex(ValueError, "requires source layout 6"):
                        resume_coding(Settings(api_key="synthetic"), root)
                    sandbox.assert_not_called()
                    client.assert_not_called()
                self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})

    def test_document_report_is_rejected_before_any_existing_artifact_is_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"label": "document-v1"}))
            (root / "summary.json").write_text('{"retained": "historical summary"}\n')
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            with self.assertRaisesRegex(ValueError, "not a coding experiment"):
                write_report(root)
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})


if __name__ == "__main__":
    unittest.main()
