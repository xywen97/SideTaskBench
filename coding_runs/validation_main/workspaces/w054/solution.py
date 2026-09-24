import json


def load_jsonl(text):
    result = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("line %d: %s" % (lineno, exc)) from exc
        if not isinstance(value, dict):
            raise ValueError("line %d: JSON value is not an object" % lineno)
        result.append(value)
    return result
