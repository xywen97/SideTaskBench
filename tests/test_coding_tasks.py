"""Validate task solvability, real defects, independent work and gold isolation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compute_bench.coding.tasks import build_coding_cases


def _run(source, tests):
    with tempfile.TemporaryDirectory(prefix="coding-fixture-") as directory:
        root = Path(directory)
        (root / "solution.py").write_text(source, encoding="utf-8")
        (root / "acceptance.py").write_text(tests, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", "acceptance.py"], cwd=root,
            capture_output=True, text=True, timeout=10,
        )


class CodingTaskTests(unittest.TestCase):
    def test_six_distinct_repositories_and_units(self):
        cases = build_coding_cases()
        self.assertEqual(len(cases), 6)
        for field in ("id", "title", "user_task", "hidden_tests"):
            self.assertEqual(len({case[field] for case in cases}), 6)
        self.assertEqual(len({case["crowd_task"]["task_id"] for case in cases}), 6)
        self.assertEqual(len({case["crowd_task"]["function_name"] for case in cases}), 6)
        self.assertEqual(len({case["crowd_task"]["library_id"] for case in cases}), 1)

    def test_every_bug_fails_both_public_and_hidden_acceptance(self):
        for case in build_coding_cases():
            for tests in (case["repo_files"]["tests/test_solution.py"], case["hidden_tests"]):
                with self.subTest(case=case["id"], tests="hidden" if tests == case["hidden_tests"] else "public"):
                    result = _run(case["repo_files"]["solution.py"], tests)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("FAILED", result.stderr)
                    self.assertNotIn("SyntaxError", result.stderr)
                    self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_reference_repairs_pass_public_and_hidden_acceptance(self):
        for case in build_coding_cases():
            for tests in (case["repo_files"]["tests/test_solution.py"], case["hidden_tests"]):
                with self.subTest(case=case["id"]):
                    result = _run(case["reference_files"]["solution.py"], tests)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("OK", result.stderr)

    def test_crowd_reference_functions_pass_independent_acceptance(self):
        for case in build_coding_cases():
            with self.subTest(case=case["id"]):
                result = _run(case["crowd_reference_code"], case["crowd_tests"])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("OK", result.stderr)

    def test_crowd_acceptance_rejects_empty_and_constant_implementations(self):
        for case in build_coding_cases():
            with self.subTest(case=case["id"]):
                signature = case["crowd_task"]["signature"]
                result = _run(f"def {signature}:\n    return None\n", case["crowd_tests"])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FAILED", result.stderr)

    def test_assembly_forms_one_importable_library(self):
        cases = build_coding_cases()
        source = "\n\n".join(case["crowd_reference_code"] for case in cases)
        for case in cases:
            with self.subTest(case=case["id"]):
                result = _run(source, case["crowd_tests"])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gold_not_in_victim_repository_or_external_spec(self):
        for case in build_coding_cases():
            public = json.dumps({
                "repo_files": case["repo_files"],
                "user_task": case["user_task"],
                "reference_text": case["reference_text"],
                "crowd_task": case["crowd_task"],
            })
            for private in ("hidden_tests", "reference_files", "crowd_tests", "crowd_reference_code"):
                self.assertNotIn(private, public)
            self.assertNotIn(case["crowd_reference_code"], "\n".join(case["repo_files"].values()))
            self.assertNotIn("AGENTS.md", case["repo_files"])
            self.assertNotIn(case["crowd_task"]["function_name"], case["user_task"])
            self.assertNotIn(case["crowd_task"]["task_id"], case["reference_text"])
            self.assertEqual(set(case["reference_files"]), {"solution.py"})

    def test_cases_are_deterministic_independent_and_json_serializable(self):
        original = build_coding_cases()
        self.assertEqual(original, build_coding_cases())
        self.assertEqual(json.loads(json.dumps(original)), original)
        original[0]["repo_files"]["solution.py"] = "changed"
        original[0]["crowd_task"]["examples"][0]["input"] = "changed"
        self.assertNotEqual(original, build_coding_cases())
        self.assertEqual(build_coding_cases(2), build_coding_cases()[:2])

    def test_invalid_count(self):
        for count in (0, 7, -1, True, "2", None):
            with self.subTest(count=count), self.assertRaises(ValueError):
                build_coding_cases(count)


if __name__ == "__main__":
    unittest.main()
