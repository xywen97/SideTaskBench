import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of objects.

    One dictionary is returned per nonblank physical line. Empty and
    whitespace-only lines are ignored, including at either end. Every
    nonblank line must decode to a JSON object; invalid JSON or a decoded
    value that is not an object raises ValueError naming the physical
    one-based line number as 'line N'.
    """
    objects = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            # Blank (empty or whitespace-only) physical line: ignore it,
            # but keep numbering tied to the original source lines.
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
