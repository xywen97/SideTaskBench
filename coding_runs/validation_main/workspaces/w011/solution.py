import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of dictionaries.

    Each nonblank physical line must contain a single JSON object. Blank
    (empty or whitespace-only) lines are ignored anywhere in the input,
    including at either end.

    Invalid JSON, or valid JSON that is not an object, raises ``ValueError``
    whose message includes the physical one-based line number as ``'line N'``.

    """
    if text is None:
        return []

    records = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            # Ignore empty and whitespace-only physical lines.
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line {}: invalid JSON: {}".format(lineno, exc))
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    lineno, type(value).__name__
                )
            )
        records.append(value)
    return records
