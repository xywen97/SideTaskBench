import json


def load_jsonl(text):
    """Parse newline-delimited JSON text into a list of objects.

    Each nonblank physical line must contain exactly one JSON object.
    Empty or whitespace-only lines are ignored, including at either end.
    Invalid JSON and valid JSON values that are not objects raise
    ``ValueError`` mentioning the physical one-based line number as
    ``line N``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line %d: invalid JSON: %s" % (lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line %d: expected JSON object, got %s"
                % (lineno, type(value).__name__)
            )
        result.append(value)
    return result
