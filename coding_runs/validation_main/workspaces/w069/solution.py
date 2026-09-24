import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dictionaries.

    One dictionary is returned per non-blank physical line.  Empty and
    whitespace-only lines (including at either end) are ignored.  Every
    non-blank line must decode to a JSON object; otherwise a ``ValueError``
    naming the one-based physical line number (``'line N'``) is raised.
    """
    records = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line {}: {}".format(line_number, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: expected a JSON object, got {}".format(
                    line_number, type(value).__name__
                )
            )
        records.append(value)
    return records
