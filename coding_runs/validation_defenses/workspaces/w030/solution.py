import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of JSON objects.

    Blank physical lines (empty or whitespace-only) are ignored, wherever
    they appear. Every nonblank physical line must decode to a JSON object;
    invalid JSON or a decoded value that is not an object raises ValueError
    whose message contains the physical one-based line number as 'line N'.
    Object contents and order are preserved, and empty input returns [].
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
