"""Task validity for the sixteen host repairs and thirty closed provider units."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from compute_bench.workloads.provider_atomic.catalog import (
    CASE_ROOT, LARGE_TASKS, _load_public_tasks, assemble_portfolio,
    atomic_task_catalog, grade_atomic,
)
from compute_bench.coding.tasks import build_coding_cases, build_run_plan, cases_for_manifest
from collections import Counter


def _run(source, tests, timeout=10):
    with tempfile.TemporaryDirectory(prefix="coding-fixture-") as directory:
        root = Path(directory)
        (root / "solution.py").write_text(source, encoding="utf-8")
        (root / "acceptance.py").write_text(tests, encoding="utf-8")
        return subprocess.run([sys.executable, "-B", "acceptance.py"], cwd=root,
                              capture_output=True, text=True, timeout=timeout)


class CodingTaskTests(unittest.TestCase):
    def test_provider_atomic_suite_has_no_coding_dependency(self):
        provider_root = CASE_ROOT.parent
        for path in provider_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("compute_bench.coding", source)
            self.assertNotIn("from ...coding", source)

    def test_atomic_tasks_are_one_json_each_grouped_by_large_task(self):
        task_files = sorted(CASE_ROOT.glob("*/*.json"))
        self.assertEqual(len(task_files), 30)
        counts = {}
        for path in task_files:
            task = json.loads(path.read_text(encoding="utf-8"))
            counts[path.parent.name] = counts.get(path.parent.name, 0) + 1
            self.assertEqual(path.stem, task["task_id"])
            self.assertEqual(path.parent.name, task["large_task_id"])
            self.assertNotIn("reference_artifact", task)
            self.assertNotIn("evaluator", task)
        self.assertEqual(counts, {key: value["total"] for key, value in LARGE_TASKS.items()})

    def test_task_json_is_the_authoritative_public_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "atomic_cases"
            shutil.copytree(CASE_ROOT, copied)
            path = copied / "atomic-function-library" / "rewrite-user-record.json"
            task = json.loads(path.read_text(encoding="utf-8"))
            task["description"] = "Definition loaded from the task JSON."
            path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            loaded = {item["task_id"]: item for item in _load_public_tasks(copied)}
            self.assertEqual(loaded["rewrite-user-record"]["description"], task["description"])

    def test_full_cross_plan_has_480_pairs_and_eight_repeats_each(self):
        cases = build_coding_cases()
        self.assertEqual(len(cases), 480)
        self.assertEqual(len({case["id"] for case in cases}), 480)
        self.assertEqual(len({case["host_task_id"] for case in cases}), 16)
        self.assertEqual(len({case["crowd_task"]["task_id"] for case in cases}), 30)
        hosts = {}
        for case in cases:
            contents = (case["repo_files"], case["user_task"], case["hidden_tests"], case["reference_text"])
            self.assertEqual(contents, hosts.setdefault(case["host_task_id"], contents))
        plan = build_run_plan(cases, ["wrapped"], ["none"])
        self.assertEqual(len(plan), 3840)
        self.assertEqual(set(Counter(p["case_id"] for p in plan).values()), {8})
        self.assertEqual(len({p["run_id"] for p in plan}), 3840)
        self.assertEqual(len({p["workspace_id"] for p in plan}), 3840)
        for case in cases:
            self.assertEqual({p["repeat"] for p in plan if p["case_id"] == case["id"]}, set(range(1, 9)))
        self.assertEqual(plan, build_run_plan(cases, ["wrapped"], ["none"]))
        self.assertNotEqual(plan, build_run_plan(cases, ["wrapped"], ["none"], seed=42))

    def test_explicit_selection_is_cartesian_and_catalog_ordered(self):
        hosts = ["coding-03", "coding-01"]
        tasks = ["regression-empty-page", "rewrite-user-record"]
        cases = build_coding_cases(host_task_ids=hosts, atomic_task_ids=tasks)
        self.assertEqual(len(cases), 4)
        self.assertEqual({(c["host_task_id"], c["crowd_task"]["task_id"]) for c in cases},
                         {(h, t) for h in hosts for t in tasks})
        self.assertEqual(cases, build_coding_cases(host_task_ids=hosts[::-1], atomic_task_ids=tasks[::-1]))
        self.assertEqual(len(build_coding_cases(host_task_ids=["coding-01"])), 30)
        self.assertEqual(len(build_coding_cases(atomic_task_ids=["rewrite-user-record"])), 16)

    def test_historical_pairing_is_read_only_compatible(self):
        cases = cases_for_manifest({"case_count": 8, "pairing_rotation": 2})
        self.assertEqual([c["id"] for c in cases], [f"coding-{i:02}" for i in range(1, 9)])
        self.assertEqual(cases[3]["crowd_task"]["task_id"], "rewrite-retry-config")
        self.assertNotIn("host_task_id", cases[0])

    def test_every_bug_fails_and_every_reference_repair_passes(self):
        for case in build_coding_cases(atomic_task_ids=["rewrite-user-record"]):
            for tests in (case["repo_files"]["tests/test_solution.py"], case["hidden_tests"]):
                with self.subTest(case=case["id"], fixed=False):
                    broken = _run(case["repo_files"]["solution.py"], tests)
                    self.assertNotEqual(broken.returncode, 0, broken.stdout + broken.stderr)
                with self.subTest(case=case["id"], fixed=True):
                    fixed = _run(case["reference_files"]["solution.py"], tests)
                    self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)

    def test_catalog_has_six_types_five_each_and_five_large_tasks(self):
        entries = atomic_task_catalog()
        self.assertEqual(len(entries), 30)
        counts, groups = {}, {}
        for entry in entries:
            task = entry["task"]
            counts[task["category"]] = counts.get(task["category"], 0) + 1
            groups[task["large_task_id"]] = groups.get(task["large_task_id"], 0) + 1
            self.assertEqual(task["material_paths"], [])
            self.assertEqual(task["atomicity"]["dependencies"], [])
            self.assertFalse(task["atomicity"]["external_context"])
            self.assertTrue(task["input"])
            self.assertTrue(task["output"])
        self.assertEqual(set(counts.values()), {5})
        self.assertEqual(groups, {key: value["total"] for key, value in LARGE_TASKS.items()})

    def test_all_reference_artifacts_pass_and_wrong_shapes_fail(self):
        for entry in atomic_task_catalog():
            with self.subTest(task=entry["task"]["task_id"]):
                self.assertTrue(grade_atomic(entry["task"], entry["reference_artifact"])["passed"])
                self.assertFalse(grade_atomic(entry["task"], {"kind": "json", "value": None})["passed"])

    def test_private_artifacts_are_not_in_public_tasks_or_host_workspaces(self):
        for case in build_coding_cases():
            public = json.dumps({key: case[key] for key in ("repo_files", "user_task", "reference_text", "crowd_task")})
            for private in ("hidden_tests", "reference_files", "crowd_evaluator", "crowd_reference_artifact"):
                self.assertNotIn(private, public)
            self.assertNotIn(case["crowd_task"]["task_id"], case["reference_text"])
            self.assertNotIn("AGENTS.md", case["repo_files"])

    def test_portfolio_reports_units_coverage_threshold_and_value(self):
        entries = atomic_task_catalog()
        plan = {"tasks": [entry["task"] for entry in entries]}
        receipts = [{"task_id": entry["task"]["task_id"], "valid": True,
                     "artifact": entry["reference_artifact"]} for entry in entries]
        with tempfile.TemporaryDirectory() as directory:
            complete = assemble_portfolio(plan, receipts, Path(directory))
            self.assertTrue(complete["final_grade"]["passed"])
            self.assertEqual(complete["completed_work_units"], 30)
            self.assertEqual(complete["coverage"], 1)
            self.assertEqual(complete["value_units_delivered"], 30)
        with tempfile.TemporaryDirectory() as directory:
            partial = assemble_portfolio(plan, receipts[:3], Path(directory))
            self.assertFalse(partial["final_grade"]["passed"])
            self.assertEqual(partial["completed_work_units"], 3)
            self.assertEqual(partial["coverage"], .1)

    def test_deterministic_json_and_valid_limits(self):
        original = build_coding_cases()
        self.assertEqual(original, build_coding_cases())
        self.assertEqual(json.loads(json.dumps(original)), original)
        original[0]["repo_files"]["solution.py"] = "changed"
        self.assertNotEqual(original, build_coding_cases())
        for field, invalid in (
            ("host_task_ids", [[], ["bad"], ["coding-01", "coding-01"], "coding-01", [1]]),
            ("atomic_task_ids", [[], ["bad"], ["rewrite-user-record", "rewrite-user-record"], [None]]),
        ):
            for value in invalid:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    build_coding_cases(**{field: value})



if __name__ == "__main__":
    unittest.main()
