import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dictionaries.

    One dictionary is returned per nonblank physical line.  Empty and
    whitespace-only lines (including leading/trailing ones) are ignored.
    Every nonblank line must decode to a JSON object; invalid JSON or a
    non-object value raises ValueError mentioning the one-based physical
    line number as ``line N``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line {}: {}".format(lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected JSON object, got {}".format(
                    lineno, type(value).__name__
                )
            )
        result.append(value)
    return result
