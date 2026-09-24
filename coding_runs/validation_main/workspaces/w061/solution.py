import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dictionaries.

    One dictionary is returned per nonblank physical line.  Empty and
    whitespace-only lines are ignored, including at either end.  Every
    nonblank line must decode to a JSON object; an invalid JSON value or a
    valid JSON value of any other type raises ``ValueError`` whose message
    contains the physical one-based line number in the form ``'line N'``.

    Object contents and their order are preserved.
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
