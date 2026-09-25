def index_pairs(pairs):
    result = {}
    for key, value in pairs:
        result.setdefault(key, []).append(value)
    return result
