"""Small JSON contracts shared by planning, assignment and collection."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import re

from .assembly import _validated_tasks as validate_tasks
from .artifacts import validated_generic_tasks


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) or value in {".", ".."}:
        raise ValueError("Identifiers must be 1-128 ASCII letters, digits, dots, underscores or hyphens")
    return value


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class TaskPlan:
    """A reviewed specification of independent, self-contained Python modules."""

    job_id: str
    objective: str
    tasks: tuple[dict, ...]
    analysis: dict
    schema_version: int = 1

    def __post_init__(self):
        identifier(self.job_id)
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("A non-empty objective is required")
        if not self.tasks:
            raise ValueError("A plan needs at least one task")
        if type(self.schema_version) is not int or self.schema_version not in {1, 2}:
            raise ValueError("Unsupported task plan version")
        generic = self.schema_version == 2 or any(isinstance(task, dict) and "artifact_kind" in task for task in self.tasks)
        if generic:
            validated_generic_tasks(list(self.tasks))
            object.__setattr__(self, "schema_version", 2)
        else:
            validate_tasks(list(self.tasks))
        for task in self.tasks:
            for field in (("description", "requirements") if generic else ("signature", "description", "requirements")):
                if not isinstance(task.get(field), str) or not task[field].strip():
                    raise ValueError(f"Task {task['task_id']} needs {field}")
            if not generic and task.get("language", "python") != "python":
                raise ValueError("The current assembler supports Python modules")
            if not isinstance(task.get("examples", []), list):
                raise ValueError("Task examples must be a list")
            if task.get("depends_on"):
                raise ValueError("This planner supports independent modules; dependent builds require another planner/assembler")
            if any(key in task for key in ("reference_code", "source_code", "gold", "tests", "crowd_tests", "acceptance_tests")):
                raise ValueError("Public task contracts must not contain implementations or private evaluators")

    def to_dict(self) -> dict:
        return copy.deepcopy({"schema_version": self.schema_version, "job_id": self.job_id, "objective": self.objective,
                              "tasks": list(self.tasks), "analysis": self.analysis})

    @classmethod
    def from_dict(cls, value: dict) -> "TaskPlan":
        if type(value.get("schema_version")) is not int or value.get("schema_version") not in {1, 2}:
            raise ValueError("Unsupported task plan version")
        return cls(value["job_id"], value["objective"], tuple(copy.deepcopy(value["tasks"])), copy.deepcopy(value["analysis"]),
                   schema_version=value["schema_version"])
