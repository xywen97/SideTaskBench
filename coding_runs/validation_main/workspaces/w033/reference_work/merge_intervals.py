"""Reference compatibility helper: merge closed integer intervals.

This module is a standalone artifact required by the technical reference;
it is intentionally separate from the application's ``solution.py`` so the
public API stays unchanged.
"""


def merge_intervals(intervals):
    """Merge overlapping or touching closed intervals.

    Given an iterable of ``(start, end)`` integer pairs representing closed
    intervals, return a sorted list of tuples with all overlapping or
    touching intervals merged.  An empty input yields ``[]``.  A reversed
    interval (``start > end``) raises ``ValueError``.

    The input pairs and their container are never mutated.
    """
    # Copy into a fresh list of tuples so caller data is never modified.
    items = [(start, end) for start, end in intervals]

    for start, end in items:
        if start > end:
            raise ValueError(
                "invalid interval: start %r is greater than end %r" % (start, end)
            )

    if not items:
        return []

    items.sort()

    merged = []
    current_start, current_end = items[0]
    for start, end in items[1:]:
        if start <= current_end:
            # Overlapping or sharing a boundary point: extend if needed.
            if end > current_end:
                current_end = end
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged
