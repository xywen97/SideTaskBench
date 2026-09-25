def merge_spans(spans):
    values = []
    for start, end in spans:
        if start > end: raise ValueError("reversed")
        values.append((start, end))
    out = []
    for start, end in sorted(values):
        if out and start <= out[-1][1]: out[-1] = (out[-1][0], max(end, out[-1][1]))
        else: out.append((start, end))
    return out
