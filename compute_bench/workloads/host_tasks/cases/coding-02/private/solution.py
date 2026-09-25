import json

def load_jsonl(text):
    records = []
    for number, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {number}: expected JSON object")
        records.append(value)
    return records
