def stable_unique(values, key=None):
    """Return the first occurrence of each distinct key, in original order.

    ``values`` may be any iterable.  When ``key`` is ``None`` the item
    itself is used as the key; otherwise ``key(item)`` is used.  Keys use
    ordinary Python equality/hash semantics and must be hashable (an
    unhashable key raises ``TypeError``).  The original first item is
    returned, not its key.  Inputs are not mutated.  Empty input returns
    ``[]``.
    """
    seen = set()
    result = []
    for item in values:
        k = item if key is None else key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result
