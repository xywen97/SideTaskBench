import json


def load_jsonl(text):
    """Decode newline-delimited JSON objects.

    Returns one dictionary per nonblank physical line of *text*.  Empty or
    whitespace-only lines are ignored, including at either end.  Invalid JSON
    and valid JSON values that are not objects raise :class:`ValueError`
    mentioning the physical one-based line number as ``line N``.
    """
    if not text.strip():
        return []

    records = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            raise ValueError(
                "invalid JSON on line %d" % line_number
            ) from None
        if not isinstance(value, dict):
            raise ValueError(
                "expected a JSON object on line %d" % line_number
            )
        records.append(value)
    return records
