import json


def load_jsonl(text):
    """Parse newline-delimited JSON objects.

    Returns one ``dict`` per nonblank physical line. Empty and
    whitespace-only lines are ignored, including at either end of the
    input. Every nonblank line must decode to a JSON object; otherwise a
    ``ValueError`` is raised whose message contains the physical one-based
    line number in the form ``"line N"``.
    """
    result = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "line {}: invalid JSON: {}".format(line_number, exc.msg)
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                "line {}: JSON value is not an object".format(line_number)
            )
        result.append(value)
    return result
