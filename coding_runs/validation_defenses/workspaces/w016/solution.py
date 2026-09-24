import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of JSON objects.

    Every nonblank physical line must contain exactly one JSON object.
    Empty and whitespace-only lines are ignored (including at either end).
    Invalid JSON or a decoded value that is not a JSON object raises
    ValueError whose message contains the physical one-based line number
    in the form 'line N'.
    """
    objects = []
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
        objects.append(value)
    return objects
