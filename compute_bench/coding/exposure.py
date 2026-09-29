"""Shared exposure detection for live runs and offline metrics."""

import json


DEFAULT_BLOCK_MARKER = "Work unit:"


def tool_result_exposes_block(result: dict, atomic_task_id: str,
                              marker: str = DEFAULT_BLOCK_MARKER) -> bool:
    """Return whether one model-visible tool result contains the assigned block."""
    text = json.dumps(result, ensure_ascii=False)
    return marker in text and atomic_task_id in text


def events_expose_block(events: list[dict], atomic_task_id: str,
                        marker: str = DEFAULT_BLOCK_MARKER) -> bool:
    """Return whether any model-visible tool result contains the assigned block."""
    return any(tool_result_exposes_block(event.get("result", {}), atomic_task_id, marker)
               for event in events)
