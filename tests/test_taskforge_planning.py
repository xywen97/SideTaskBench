"""Public requirement contracts and the replaceable planning boundary."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from taskforge import SpecificationPlanner, TaskForge, TaskPlan


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((Path(__file__).resolve().parents[1] /
                                  "taskforge/examples/request.json").read_text())

    def test_catalog_selection_preserves_requested_order_and_detaches_input(self):
        tasks = self.request["components"]
        expected = copy.deepcopy(list(reversed(tasks)))
        planner = SpecificationPlanner(tasks)
        request = {"job_id": "catalog-demo", "objective": "Build the selected utilities.",
                   "task_ids": [task["task_id"] for task in expected]}
        tasks[0]["description"] = "mutated caller input"
        plan = planner.plan(request)
        self.assertEqual(list(plan.tasks), expected)
        self.assertFalse(plan.analysis["natural_language_decomposition"])
        self.assertEqual(plan.analysis["strategy"], "explicit_catalog_selection")

    def test_ambiguous_missing_unknown_or_duplicate_selections_fail(self):
        planner = SpecificationPlanner(self.request["components"])
        task_id = self.request["components"][0]["task_id"]
        base = {"job_id": "selection", "objective": "Build selected components."}
        for fields in ({}, {"components": [], "task_ids": []}, {"task_ids": ["missing"]},
                       {"task_ids": [task_id, task_id]}, {"task_ids": task_id}, {"components": []}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                planner.plan({**base, **fields})
        with self.assertRaisesRegex(ValueError, "Duplicate catalog"):
            SpecificationPlanner([self.request["components"][0]] * 2)

    def test_dependent_or_private_implementation_specs_cannot_be_public_plans(self):
        changes = ({"depends_on": ["another-task"]}, {"language": "javascript"},
                   {"reference_code": "private implementation"}, {"acceptance_tests": "private tests"},
                   {"signature": ""}, {"requirements": ""}, {"examples": "unstructured"})
        for change in changes:
            request = copy.deepcopy(self.request)
            request["components"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                SpecificationPlanner().plan(request)

    def test_custom_planner_supplies_a_frozen_plan_without_a_builtin_llm(self):
        task = self.request["components"][0]

        class CustomPlanner:
            def plan(self, request):
                return TaskPlan(request["job_id"], request["objective"], (copy.deepcopy(task),),
                                {"planner": "custom-test-planner"})

        request = {"job_id": "custom", "objective": "Caller-planned utility."}
        with tempfile.TemporaryDirectory(prefix="tf-plan-") as temporary:
            directory = Path(temporary) / "job"
            job = TaskForge.create(directory, request, planner=CustomPlanner())
            self.assertEqual(job.plan["tasks"], [task])
            self.assertEqual(job.plan["analysis"]["planner"], "custom-test-planner")
            self.assertEqual(TaskForge(directory).plan, job.plan)
            self.assertEqual(job.status()["completed_tasks"], 0)


if __name__ == "__main__":
    unittest.main()
