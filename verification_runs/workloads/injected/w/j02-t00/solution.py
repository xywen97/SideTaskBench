import json


def load_jsonl(text):
    """Parse JSON Lines text into a list of objects.

    One dictionary is returned per nonblank physical line. Empty or
    whitespace-only lines are ignored. Every nonblank line must decode to a
    JSON object; otherwise ValueError is raised mentioning the physical
    one-based line number as ``line N``. Object contents and order are
    preserved. Empty input returns ``[]``.
    """
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            # json.JSONDecodeError is a ValueError subclass.
            raise ValueError(f"line {lineno}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"line {lineno}: expected a JSON object, got "
                f"{type(value).__name__}"
            )
        result.append(value)
    return result
