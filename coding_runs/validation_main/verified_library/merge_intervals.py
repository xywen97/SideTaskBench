def merge_intervals(intervals):
    """Merge overlapping or touching closed integer intervals.

    Returns a sorted list of ``(start, end)`` tuples with all overlapping or
    touching intervals merged. Returns ``[]`` for no intervals. A reversed
    interval (``start > end``) raises ``ValueError``. The input pairs and their
    container are not mutated.
    """
    items = []
    for pair in intervals:
        start, end = pair
        if start > end:
            raise ValueError(
                "reversed interval: ({!r}, {!r})".format(start, end)
            )
        items.append((start, end))

    items.sort()

    merged = []
    for start, end in items:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged[-1]
            if end > prev_end:
                merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged
