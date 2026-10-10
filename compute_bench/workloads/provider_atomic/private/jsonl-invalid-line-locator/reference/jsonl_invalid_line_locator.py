import json


def jsonl_invalid_line_locator(jsonl_text):
    invalid = []
    for number, line in enumerate(jsonl_text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            invalid.append(number)
    return invalid
