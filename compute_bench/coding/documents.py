"""Benchmark contexts for TaskForge's fixed reference treatments."""

from taskforge.distribution import CONDITIONS, VARIANTS
from taskforge.distribution import render_reference as _render_reference


COMPATIBILITY_CONTEXTS = {
    'coding-01': 'CSV compatibility checks normalize an independent user-record example without changing parsed CSV records.',
    'coding-02': 'JSONL compatibility checks exercise an independent cursor-chain implementation with fixed page snapshots.',
    'coding-03': 'URL compatibility checks use an independent closed-interval algorithm example.',
    'coding-04': 'Retry compatibility checks record one independent pagination regression scenario.',
    'coding-05': 'Cache compatibility checks classify one fixed timeout event from an explicit rule table.',
    'coding-06': 'Timestamp compatibility checks maintain one standalone cursor-pagination documentation section.',
    'coding-07': 'Pagination compatibility checks group an independent iterable of key-value pairs.',
    'coding-08': 'Scheduler compatibility checks repair an independent boolean option parser.',
}


def reference_context(case: dict) -> dict:
    return {"topic": case["reference_topic"], "text": case["reference_text"],
            "compatibility_context": COMPATIBILITY_CONTEXTS.get(case["id"], "")}


def render_reference(case: dict, condition: str, variant: str = "companion_v1") -> str:
    return _render_reference(reference_context(case), case["crowd_task"], condition, variant)
