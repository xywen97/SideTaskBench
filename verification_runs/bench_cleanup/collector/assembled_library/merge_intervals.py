def merge_intervals(intervals):
    normalized = []
    for pair in intervals:
        start, end = pair
        if start > end:
            raise ValueError("reversed interval")
        normalized.append((start, end))
    normalized.sort()
    merged = []
    for start, end in normalized:
        if merged and start <= merged[-1][1]:
            ps, pe = merged[-1]
            merged[-1] = (ps, max(pe, end))
        else:
            merged.append((start, end))
    return merged
