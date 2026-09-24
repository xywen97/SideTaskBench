"""Replaceable planning interface; the default decomposes explicit specifications."""

import copy
from typing import Protocol

from .models import TaskPlan, identifier


class Planner(Protocol):
    def plan(self, request: dict) -> TaskPlan: ...


class SpecificationPlanner:
    """Validate requested components or select known components from a catalog.

    The objective is user text, not an instruction to fabricate a decomposition.
    An LLM-based planner can implement the same interface later. Acceptance code
    stays with a trusted evaluator and is never part of the public task plan.
    """

    def __init__(self, catalog=()):
        self.catalog = {}
        for task in catalog:
            if not isinstance(task, dict):
                raise ValueError("Catalog entries must be public task objects")
            task_id = identifier(task.get("task_id"))
            if task_id in self.catalog:
                raise ValueError("Duplicate catalog task: " + task_id)
            self.catalog[task_id] = copy.deepcopy(task)

    def plan(self, request: dict) -> TaskPlan:
        if not isinstance(request, dict):
            raise ValueError("Requirement must be a JSON object")
        explicit, selection = request.get("components"), request.get("task_ids")
        if (explicit is None) == (selection is None):
            raise ValueError("Provide either components or task_ids with a catalog")
        if explicit is not None:
            if not isinstance(explicit, list):
                raise ValueError("components must be a list")
            tasks = copy.deepcopy(explicit)
            strategy = "explicit_component_specification"
        else:
            if not isinstance(selection, list) or not all(isinstance(item, str) for item in selection):
                raise ValueError("task_ids must be a list of catalog identifiers")
            if len(selection) != len(set(selection)):
                raise ValueError("Repeated task_ids are not a decomposition")
            missing = set(selection) - self.catalog.keys()
            if missing:
                raise ValueError("Unknown catalog tasks: " + ", ".join(sorted(missing)))
            tasks = [copy.deepcopy(self.catalog[item]) for item in selection]
            strategy = "explicit_catalog_selection"
        return TaskPlan(request["job_id"], request["objective"], tuple(tasks), {
            "planner": "SpecificationPlanner", "strategy": strategy, "unit_count": len(tasks),
            "assembly": "one independent Python module per component, exported by __init__.py",
            "natural_language_decomposition": False,
        })
