"""Bind public TaskForge jobs to the benchmark's private acceptance evaluator."""

from contextlib import contextmanager
from pathlib import Path

from taskforge import TaskForge

from compute_bench.workloads.provider_atomic import (
    assemble_portfolio,
    grade_atomic,
    public_atomic_tasks,
)


EVALUATOR_ID = "compute_bench.workloads.provider_atomic.grade_atomic:v3"


def public_request(cases: list[dict]) -> dict:
    """Publish all 30 closed units; a run exposes only its frozen pairing."""
    return {
        "job_id": "coding-atomic-portfolio-v1",
        "objective": "Assemble five large deliverables from thirty independent atomic work units.",
        "components": public_atomic_tasks(),
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
    bindings = {case["id"]: case["crowd_task"]["task_id"] for case in cases}
    if len(bindings) != len(cases):
        raise ValueError("Benchmark pair identifiers must be unique")

    def grade(task, artifact):
        return grade_atomic(task, artifact)

    with platform.session(grade, evaluator_id=EVALUATOR_ID, bindings=bindings):
        yield platform


def assemble_platform(platform: TaskForge) -> dict:
    return platform.assemble(assembler=assemble_portfolio)
