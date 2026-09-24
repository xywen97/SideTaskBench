import json


def load_jsonl(text):
    """Parse newline-delimited JSON text into a list of objects.

    Each nonblank physical line must contain exactly one JSON object.
    Empty or whitespace-only lines are ignored, including leading and
    trailing ones.  Invalid JSON, or valid JSON that is not an object,
    raises ValueError whose message contains the physical one-based
    line number in the form ``line N``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            # Blank (empty or whitespace-only) physical line: skip it,
            # but keep counting so later errors report real line numbers.
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line %d: invalid JSON: %s" % (lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line %d: expected a JSON object, got %s"
                % (lineno, type(value).__name__)
            )
        result.append(value)
    return result
