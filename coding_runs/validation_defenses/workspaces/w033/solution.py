import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of objects.

    Blank (empty or whitespace-only) physical lines are ignored. Every
    nonblank line must contain a single JSON object; otherwise a
    ValueError naming the physical one-based line number is raised.
    """
    objects = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"line {line_number}: expected a JSON object, "
                f"got {type(value).__name__}"
            )
        objects.append(value)
    return objects
