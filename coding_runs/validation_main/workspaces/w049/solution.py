import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of objects.

    One dictionary is returned per nonblank physical line. Empty or
    whitespace-only lines (including at either end) are ignored. Every
    nonblank line must decode to a JSON object; any invalid JSON or valid
    JSON value that is not an object raises ``ValueError`` mentioning the
    physical one-based line number as ``line N``.

    Object contents and order are preserved and erroneous nonblank lines
    are never skipped. Empty input returns ``[]``.
    """
    records = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"line {lineno}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {lineno}")
        records.append(value)
    return records
