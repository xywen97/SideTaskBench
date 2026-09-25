def map_status(value):
    key = value.strip().casefold()
    mapping = {"queued": "pending", "running": "active", "done": "complete"}
    if key not in mapping:
        raise ValueError("unknown status")
    return mapping[key]
