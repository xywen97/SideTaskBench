"""Public JSONL traces; private reasoning is only retained in model context."""

import json
from pathlib import Path


def public_message(message: dict) -> dict:
    """Store actions and visible answers; do not publish the model's hidden reasoning."""
    return {k: v for k, v in message.items() if k in {"role", "content", "tool_calls", "tool_call_id", "name"}}


def append_event(path: Path, event: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


