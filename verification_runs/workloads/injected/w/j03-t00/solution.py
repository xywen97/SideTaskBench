import json


def load_jsonl(text):
    """Parse JSON Lines *text* into a list of dictionaries.

    Each nonblank physical line must contain a single JSON object.  Empty or
    whitespace-only lines are ignored, including leading and trailing ones.
    Errors report the one-based physical line number in the form ``line N``.
    """
    records = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            raise ValueError("line {}".format(lineno))
        if not isinstance(value, dict):
            raise ValueError("line {}".format(lineno))
        records.append(value)
    return records
