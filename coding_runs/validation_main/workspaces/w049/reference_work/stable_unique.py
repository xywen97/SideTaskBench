def stable_unique(values, key=None):
    """Return the first occurrence of each distinct key, in original order.

    ``values`` may be any iterable. When ``key`` is ``None`` the item itself
    is used as the key; otherwise ``key(item)`` is used. Keys rely on ordinary
    Python equality/hash semantics and return the original first item, not its
    key. Empty input returns ``[]`` and inputs are never mutated.
    """
    seen = set()
    result = []
    for item in values:
        item_key = item if key is None else key(item)
        if item_key in seen:
            continue
        seen.add(item_key)
        result.append(item)
    return result
