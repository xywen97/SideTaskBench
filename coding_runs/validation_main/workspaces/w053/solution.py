import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dictionaries.

    One dictionary is returned per nonblank physical line.  Empty and
    whitespace-only lines (including leading and trailing ones) are ignored.

    Every nonblank line must decode to a JSON object.  Invalid JSON, and
    valid JSON values that are not objects, raise ``ValueError`` whose message
    contains the physical one-based line number in the form ``line N``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            # Blank or whitespace-only physical line: ignore it without
            # disturbing the numbering of the remaining lines.
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(
                "line {}: invalid JSON: {}".format(lineno, exc)
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    lineno, type(value).__name__
                )
            )
        result.append(value)
    return result
