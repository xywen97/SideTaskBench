import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dicts.

    Each nonblank physical line must contain a single JSON object. Empty or
    whitespace-only lines are ignored. Invalid JSON, or valid JSON that is not
    an object, raises ``ValueError`` mentioning the physical one-based line
    number as ``line N``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line {}: invalid JSON: {}".format(lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    lineno, type(value).__name__
                )
            )
        result.append(value)
    return result
