from datetime import datetime, timezone

def parse_timestamp(value):
    return datetime.fromisoformat(value.rstrip("Z")).replace(tzinfo=timezone.utc)
