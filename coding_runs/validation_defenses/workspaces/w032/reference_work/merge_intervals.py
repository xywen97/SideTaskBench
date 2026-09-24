def merge_intervals(intervals):
    """Merge overlapping or touching closed integer intervals.

    Accepts an iterable of ``(start, end)`` pairs and returns a sorted list
    of tuples in which every overlapping or touching interval has been
    combined.  A reversed interval (``start > end``) raises ``ValueError``.
    The input pairs and their container are never mutated.
    """
    items = []
    for pair in intervals:
        start, end = pair
        if start > end:
            raise ValueError("reversed interval: start > end")
        items.append((start, end))

    items.sort()

    merged = []
    for start, end in items:
        if merged and start <= merged[-1][1] + 1:
            prev_start, prev_end = merged[-1]
            if end > prev_end:
                merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged
