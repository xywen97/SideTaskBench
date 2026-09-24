import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of dictionaries.

    Blank (empty or whitespace-only) physical lines are ignored. Every
    nonblank physical line must decode to a JSON object. Invalid JSON or
    a decoded value that is not an object raises ValueError mentioning the
    physical one-based line number as 'line N'.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"line {lineno}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"line {lineno}: expected a JSON object, got {type(value).__name__}"
            )
        result.append(value)
    return result
