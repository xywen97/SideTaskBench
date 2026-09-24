"""Executable compatibility check: merge closed integer intervals.

Merges overlapping or touching closed intervals in ``(start, end)`` form.
Inputs are not mutated.
"""


def merge_intervals(intervals):
    """Return sorted, merged (start, end) tuples for the given intervals.

    Overlapping or touching intervals (``next_start <= current_end``) are
    merged. An empty iterable yields ``[]``. A reversed interval
    (``start > end``) raises ``ValueError``. The input container and its
    pairs are left untouched.
    """
    pairs = []
    for interval in intervals:
        start, end = interval[0], interval[1]
        if start > end:
            raise ValueError("reversed interval: start > end (%r, %r)" % (start, end))
        pairs.append((start, end))

    pairs.sort()

    merged = []
    for start, end in pairs:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged[-1]
            if end > prev_end:
                merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    return merged
