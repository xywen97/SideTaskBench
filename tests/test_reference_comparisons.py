"""Reference evidence stays readable and independent of mutable Agent workspaces."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.documents import render_reference
from compute_bench.coding.report import reference_comparison_report, write_report
from compute_bench.coding.runner import execute_coding
from compute_bench.coding.tasks import build_coding_cases
from microcoder.config import Settings


class ReferenceComparisonTests(unittest.TestCase):
    def test_wrapped_only_freezes_actual_reference_before_bootstrap_and_reports_without_llm(self):
        case = build_coding_cases(host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"])[0]
        case["reference_text"] += '\n<script>alert("reference")</script>\n'
        before = render_reference(case, "clean", "compatibility_v3")
        after = render_reference(case, "wrapped", "compatibility_v3")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"

            def bootstrap(actual_case, workspace, condition, variant):
                frozen = root / "reference_comparisons" / case["id"] / condition
                self.assertEqual((frozen / "after.md").read_text(), render_reference(actual_case, condition, variant))
                # Even bootstrap failure must leave a comparison report, without a model call.
                raise RuntimeError("synthetic bootstrap failure")

            with patch("compute_bench.coding.runner.build_coding_cases", return_value=[case]), \
                 patch("compute_bench.coding.runner.Sandbox") as sandbox, \
                 patch("compute_bench.coding.runner.create_workspace", side_effect=bootstrap) as create, \
                 patch("compute_bench.coding.runner.ChatClient") as client, \
                 redirect_stdout(io.StringIO()) as output:
                sandbox.probe.return_value = {"available": True}
                with self.assertRaisesRegex(RuntimeError, "failed in the harness"):
                    execute_coding(Settings(api_key="synthetic"), root, host_task_ids=["coding-01"], atomic_task_ids=["rewrite-user-record"],
                                   conditions=["wrapped"], repeats=2, workers=2)
                client.assert_not_called()
                self.assertEqual(create.call_count, 2)

            plan = json.loads((root / "plan.json").read_text())
            self.assertEqual({trial["condition"] for trial in plan}, {"wrapped"})
            entries = json.loads((root / "reference_comparisons/index.json").read_text())
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(set(entry["run_ids"]), {trial["run_id"] for trial in plan})
            self.assertEqual((root / entry["before"]).read_text(), before)
            self.assertEqual((root / entry["after"]).read_text(), after)
            diff = (root / entry["diff"]).read_text()
            self.assertIn("+## Executable compatibility check", diff)
            self.assertIn(case["crowd_task"]["task_id"], diff)
            self.assertIn(diff, output.getvalue())
            self.assertIn(diff, (root / "reference_comparisons.log").read_text())
            page = (root / "report.html").read_text()
            self.assertIn("reference.md 嵌入前后对比", page)
            self.assertIn('class="added"', page)
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn("<script>", page)
            self.assertNotIn("crowd_reference_artifact", page)

            # Rebuilding the report reads frozen evidence, never the current renderer.
            with patch("compute_bench.coding.documents.render_reference", side_effect=AssertionError("must not rerender")):
                write_report(root)
            self.assertEqual((root / "report.html").read_text(), page)

    def test_old_runs_explicitly_report_missing_comparisons(self):
        with tempfile.TemporaryDirectory() as temporary:
            markdown, page = reference_comparison_report(Path(temporary))
            self.assertIn("未保存前后对比快照", "\n".join(markdown))
            self.assertIn("未保存前后对比快照", page)


if __name__ == "__main__":
    unittest.main()
