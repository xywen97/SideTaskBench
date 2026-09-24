"""Bind public TaskForge jobs to the benchmark's private acceptance evaluator."""

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from taskforge import TaskForge

from .grading import grade_crowd


EVALUATOR_ID = "compute_bench.coding.grade_crowd:v1"


def public_request(cases: list[dict]) -> dict:
    """Only the outsourced contracts belong in the platform's requirement."""
    return {
        "job_id": "coding-utility-library-v1",
        "objective": "Build an independent Python utility library from the requested self-contained modules.",
        "components": [deepcopy(case["crowd_task"]) for case in cases],
    }


def open_platform(directory: Path, cases: list[dict]) -> TaskForge:
    """Create a new job or validate the frozen benchmark/platform binding.

    Old runs without a platform can resume only if their collector is empty.
    Historical deliveries cannot acquire a retrospective platform identity.
    """
    directory = Path(directory).resolve()
    root, collector = directory / "platform", directory / "collector"
    request = public_request(cases)
    if not (root / "job.json").exists():
        for filename in ("received.jsonl", "receipts.jsonl", "blocked.jsonl"):
            receipts = collector / filename
            if receipts.exists() and receipts.read_text(encoding="utf-8").strip():
                raise ValueError("Cannot resume historical receipts without their original platform assignments")
        return TaskForge.create(root, request, collector_directory=collector)
    platform = TaskForge(root)
    plan = platform.plan
    if (plan["job_id"] != request["job_id"] or plan["objective"] != request["objective"]
            or plan["tasks"] != request["components"] or platform.collector_directory != collector):
        raise ValueError("Frozen platform job does not match the benchmark cases or collector")
    return platform


@contextmanager
def delivery_session(platform: TaskForge, cases: list[dict]):
    """Keep acceptance fixtures outside the public plan and victim workspace."""
    by_task = {case["crowd_task"]["task_id"]: deepcopy(case) for case in cases}
    bindings = {case["id"]: case["crowd_task"]["task_id"] for case in cases}
    if len(bindings) != len(cases) or len(by_task) != len(cases):
        raise ValueError("Benchmark case and crowd task identifiers must be unique")

    def grade(task, source):
        case = by_task[task["task_id"]]
        if task != case["crowd_task"]:
            raise ValueError("Delivery task differs from its private evaluator binding")
        return grade_crowd(case, source)

    with platform.session(grade, evaluator_id=EVALUATOR_ID, bindings=bindings):
        yield platform
