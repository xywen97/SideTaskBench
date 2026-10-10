def rst_border_column_spans(border_line):
    widths = [len(segment) for segment in border_line.strip().split("+")[1:-1]]
    return {"column_count": len(widths), "column_widths": widths}
