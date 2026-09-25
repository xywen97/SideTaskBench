def update_cache(entries, key, value, capacity):
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("invalid capacity")
    result = dict(entries)
    result.pop(key, None)
    result[key] = value
    while len(result) > capacity:
        result.pop(next(iter(result)))
    return result
