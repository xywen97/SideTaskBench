import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from taskforge.collection import ResultCollector
from compute_bench.coding.grading import grade_crowd
from compute_bench.coding.tasks import build_coding_cases
from compute_bench.coding.environment import CodingEnvironment
from compute_bench.coding.runner import scan_work
from compute_bench.coding.rescore import rescore_directory
from test_coding_audit import _fixture


class CorrectedAcceptanceTests(unittest.TestCase):
    def test_rescore_ignores_post_trial_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root, delivered=False)
            case = build_coding_cases(1)[0]
            (root / "workspaces/w000/added_after_trial.py").write_text(case["crowd_reference_code"])
            rescore_directory(root, workers=1)
            corrected = json.loads((root / "corrected_results.jsonl").read_text())
            self.assertEqual(corrected["observed_work"], [])
            self.assertFalse(corrected["correct_work_observed"])

    def test_rescore_rejects_modified_workspace_before_grading_or_writing_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root)
            (root / "workspaces/w000/solution.py").write_text("# altered after trial\n")
            with patch("compute_bench.coding.rescore.grade_main", side_effect=AssertionError("must not grade changed evidence")):
                with self.assertRaisesRegex(ValueError, "inconsistent original evidence"):
                    rescore_directory(root)
            self.assertFalse((root / "corrected_results.jsonl").exists())

    def test_deleted_extra_work_is_visible_only_from_successful_recorded_write(self):
        case = build_coding_cases(1)[0]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            env = CodingEnvironment(case, workspace, "wrapped")
            args = {"path": "/workspace/extra.py", "content": case["crowd_reference_code"]}
            self.assertIn("written", env.execute("write_file", args))
            # A duplicate write is one source candidate, and failed writes are not artifacts.
            env.execute("write_file", args)
            env.execute("write_file", {**args, "path": "../escape.py"})
            (workspace / "extra.py").unlink()
            self.assertEqual(scan_work(case, workspace), [])
            observed = scan_work(case, workspace, env.events)
            self.assertEqual(len(observed), 1)
            self.assertTrue(observed[0]["grade"]["passed"])
            self.assertEqual(observed[0]["provenance"], "trace_write_file")
            self.assertEqual(observed[0]["event_index"], 0)
            self.assertEqual(observed[0]["source_code"], args["content"])
            self.assertEqual(scan_work(case, workspace, env.events[-1:]), [])

    def test_topological_iterator_edges_must_not_disappear(self):
        case = build_coding_cases()[-1]
        flawed = '''import heapq
def topological_sort(graph):
    nodes = set(graph)
    for deps in graph.values(): nodes.update(deps)
    edges = {node: set(graph.get(node, [])) for node in nodes}
    output = []
    while edges:
        ready = sorted(node for node, deps in edges.items() if not deps)
        if not ready: raise ValueError('cycle')
        node = ready[0]
        output.append(node)
        del edges[node]
        for deps in edges.values(): deps.discard(node)
    return output
'''
        self.assertFalse(grade_crowd(case, flawed)["passed"])
        self.assertTrue(grade_crowd(case, case["crowd_reference_code"])["passed"])

    def test_collector_restart_preserves_registration_without_duplicate_rows(self):
        cases = build_coding_cases(1)
        with tempfile.TemporaryDirectory(prefix="col-restart-") as directory:
            root = Path(directory)
            state = root / "state"
            sock = root / "c.sock"
            assignments = [{"id": case["id"], "task": case["crowd_task"]} for case in cases]
            by_task = {case["crowd_task"]["task_id"]: case for case in cases}
            def grader(task, source):
                return grade_crowd(by_task[task["task_id"]], source)
            with ResultCollector(state, assignments, grader) as collector:
                collector.register_run("r1", cases[0]["id"], sock)
            with ResultCollector(state, assignments, grader) as collector:
                collector.register_run("r1", cases[0]["id"], sock)
                self.assertEqual(collector.get_receipts("r1"), [])
                self.assertFalse(collector.aggregate()["large_task_complete"])
            lines = (state / "registrations.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["run_id"], "r1")


if __name__ == "__main__":
    unittest.main()
