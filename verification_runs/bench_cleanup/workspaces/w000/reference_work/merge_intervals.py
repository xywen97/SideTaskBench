"""Reference compatibility helper: merge overlapping/touching closed intervals."""


def merge_intervals(intervals):
    """Merge overlapping or touching closed integer intervals.

    Returns a new, sorted list of (start, end) tuples. Two intervals are
    merged when they overlap or share an endpoint (``start <= prev_end``).
    Raises ValueError for any reversed interval (start > end). The input is
    neither mutated nor consumed beyond a single pass.
    """
    normalized = []
    for pair in intervals:
        start, end = pair
        if start > end:
            raise ValueError("reversed interval: (%r, %r)" % (start, end))
        normalized.append((start, end))

    normalized.sort()

    merged = []
    for start, end in normalized:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged
