"""Greedy weight-bounded chunking helper.

Self-contained standard-library implementation of ``chunk_by_weight`` as
described by the repository's technical reference document.
"""


def chunk_by_weight(items, limit, weight=None):
    """Greedily partition ``items`` into consecutive nonempty chunks.

    Each chunk's total weight is at most ``limit``. Order is preserved and
    input objects are never mutated. ``weight`` is an optional callable used
    to compute each item's weight; without it each item is its own weight.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if weight is not None and not callable(weight):
        raise ValueError("weight must be callable or None")

    chunks = []
    current = []
    total = 0
    for item in items:
        item_weight = weight(item) if weight is not None else item
        if (
            isinstance(item_weight, bool)
            or not isinstance(item_weight, int)
            or item_weight < 0
            or item_weight > limit
        ):
            raise ValueError("each weight must be an integer in [0, limit]")
        if current and total + item_weight > limit:
            chunks.append(current)
            current = []
            total = 0
        current.append(item)
        total += item_weight
    if current:
        chunks.append(current)
    return chunks
