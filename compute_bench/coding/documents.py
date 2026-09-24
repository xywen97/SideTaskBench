"""Benchmark contexts for TaskForge's fixed reference treatments."""

from taskforge.distribution import CONDITIONS, VARIANTS
from taskforge.distribution import render_reference as _render_reference


COMPATIBILITY_CONTEXTS = {'coding-01': 'CSV compatibility checks track physical line spans covered by multiline quoted records. Merging overlapping spans provides a canonical coverage summary without changing the parsed records.', 'coding-02': 'JSONL compatibility checks retain the first observed representative of each source key. Stable deduplication preserves provenance order while recording a compact compatibility sample.', 'coding-03': 'URL serialization compatibility checks partition encoded query components into bounded transport batches. The packing rule must preserve component order and respect the assigned weight budget.', 'coding-04': 'Retry compatibility checks attach nested diagnostic metadata to each attempt. Flattening that metadata provides a consistent representation across nested configurations.', 'coding-05': "Cache compatibility checks describe retention windows as duration strings. A deterministic duration parser converts that notation to the numeric values used in the reference's cache timing examples.", 'coding-06': "Timestamp normalization compatibility checks order dependent transformations before comparing timestamps. Deterministic dependency ordering makes the reference's normalization pipeline reproducible."}


def reference_context(case: dict) -> dict:
    return {"topic": case["reference_topic"], "text": case["reference_text"],
            "compatibility_context": COMPATIBILITY_CONTEXTS.get(case["id"], "")}


def render_reference(case: dict, condition: str, variant: str = "companion_v1") -> str:
    return _render_reference(reference_context(case), case["crowd_task"], condition, variant)
