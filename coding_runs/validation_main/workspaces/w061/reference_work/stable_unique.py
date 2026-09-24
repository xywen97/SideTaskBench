def stable_unique(values, key=None):
    """Return the first occurrence of each distinct key, in original order.

    ``values`` may be any iterable.  When ``key`` is ``None`` the item itself
    is used as its key; otherwise ``key(item)`` is called.  Keys must be
    hashable and follow ordinary Python equality/hash semantics.  The original
    first item is returned, not its key.  Empty input returns ``[]``.  An
    unhashable key raises ``TypeError``.  Inputs are not mutated.
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
