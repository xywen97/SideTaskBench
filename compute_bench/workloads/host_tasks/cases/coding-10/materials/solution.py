def merge_headers(base, updates):
    values = dict(base)
    values.update(updates)
    return list(values.items())
