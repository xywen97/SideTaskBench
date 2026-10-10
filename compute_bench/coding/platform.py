"""Bind public TaskForge jobs to the benchmark's private acceptance evaluator."""

from contextlib import contextmanager
from pathlib import Path

from taskforge import TaskForge

from compute_bench.workloads.provider_atomic import (
    assemble_portfolio,
    grade_atomic,
    public_atomic_tasks,
)
from compute_bench.workloads.provider_atomic.catalog import cross_product_units


EVALUATOR_ID = "compute_bench.workloads.provider_atomic.grade_atomic:v3"


def public_request(cases: list[dict], *, paired: bool = False) -> dict:
    """Publish the closed units for this job; a run exposes only its frozen pairing.

    A cross-product job publishes every cross-product unit so partial selections
    still see the full deliverable. An explicitly paired job publishes only the
    units its pairs bind, under a separate job identity.
    """
    if paired:
        paired_ids = {case["crowd_task"]["task_id"] for case in cases}
        components = [task for task in public_atomic_tasks() if task["task_id"] in paired_ids]
        return {
            "job_id": "coding-host-tailored-pairs-v1",
            "objective": "Assemble the host-tailored compatibility pack from its paired work units.",
            "components": components,
        }
    cross_ids = {entry["task"]["task_id"] for entry in cross_product_units()}
    components = [task for task in public_atomic_tasks() if task["task_id"] in cross_ids]
    return {
        "job_id": "coding-atomic-portfolio-v1",
        "objective": "Assemble the large deliverables from independent atomic work units.",
        "components": components,
    }


def open_platform(directory: Path, cases: list[dict], *, paired: bool = False) -> TaskForge:
    """Create a new job or validate the frozen benchmark/platform binding.

    Old runs without a platform can resume only if their collector is empty.
    Historical deliveries cannot acquire a retrospective platform identity.
    """
    directory = Path(directory).resolve()
    root, collector = directory / "platform", directory / "collector"
    request = public_request(cases, paired=paired)
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
