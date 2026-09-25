import json

def load_jsonl(text):
    if not text.strip():
        return []
    return [json.loads(line) for line in text.strip().split("\n")]
