import json


def load_jsonl(text):
    """Parse newline-delimited JSON, one object per nonblank physical line.

    Blank (empty/whitespace-only) lines are ignored. Any nonblank line that
    is not a JSON object raises ``ValueError`` mentioning its physical
    one-based line number as ``line N``.
    """
    records = []
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
        records.append(value)
    return records
