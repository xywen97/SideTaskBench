import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of JSON objects.

    Nonblank physical lines are parsed in order. Empty or whitespace-only
    lines (including leading/trailing ones) are ignored. Every nonblank line
    must decode to a JSON object; otherwise a ValueError is raised that
    includes the one-based physical line number in the form ``line N``.
    """
    records = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "line {}: invalid JSON".format(line_number)
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    line_number, type(value).__name__
                )
            )
        records.append(value)
    return records
