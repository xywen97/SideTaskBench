import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of JSON objects.

    One dictionary is returned per nonblank physical line.  Empty and
    whitespace-only lines (including leading/trailing ones) are ignored.
    Every nonblank line must decode to a JSON object; any other outcome
    raises :class:`ValueError` mentioning the physical one-based line
    number as ``line N``.
    """
    objects = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line %d: invalid JSON: %s" % (lineno, exc))
        if not isinstance(value, dict):
            raise ValueError(
                "line %d: expected a JSON object, got %s"
                % (lineno, type(value).__name__)
            )
        objects.append(value)
    return objects
