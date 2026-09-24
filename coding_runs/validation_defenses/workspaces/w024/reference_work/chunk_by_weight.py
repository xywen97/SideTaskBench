"""Reference compatibility helper: greedily partition items by weight.

Function signature: chunk_by_weight(items, limit, weight=None)
"""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def chunk_by_weight(items, limit, weight=None):
    """Greedily partition ``items`` into consecutive nonempty chunks.

    Each chunk's total weight is at most ``limit``. Item order is preserved.
    Each next item is placed in the current chunk if it fits, otherwise a new
    chunk is started. ``weight`` is an optional callable returning an item's
    weight; without it each item is its own weight.
    """
    if not _is_int(limit) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    if weight is not None and not callable(weight):
        raise ValueError("weight must be callable")

    chunks = []
    current = []
    current_weight = 0

    for item in items:
        item_weight = item if weight is None else weight(item)
        if not _is_int(item_weight) or item_weight < 0 or item_weight > limit:
            raise ValueError("weight must be a nonnegative integer <= limit")

        if current and current_weight + item_weight > limit:
            chunks.append(current)
            current = []
            current_weight = 0

        current.append(item)
        current_weight += item_weight

    if current:
        chunks.append(current)

    return chunks
