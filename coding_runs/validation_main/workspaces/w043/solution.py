import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of dictionaries.

    Each nonblank physical line must contain one JSON object. Blank
    (empty or whitespace-only) lines are ignored, including leading and
    trailing ones. Lines are numbered by their physical position in
    ``text`` (one-based), so error messages refer to the original source.
    """
    records = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line {}: {}".format(lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    lineno, type(value).__name__
                )
            )
        records.append(value)
    return records
