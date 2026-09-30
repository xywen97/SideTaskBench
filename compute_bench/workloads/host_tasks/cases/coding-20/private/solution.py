"""Read and write a small fixed-width reStructuredText table format."""


def _validate_columns(columns, header_rows):
    if not isinstance(columns, list) or not columns:
        raise ValueError("columns must be a nonempty list")
    if (not isinstance(header_rows, tuple) or not header_rows
            or "name" not in header_rows):
        raise ValueError("header_rows must be a nonempty tuple containing name")
    if (len(set(header_rows)) != len(header_rows) or "values" in header_rows
            or any(not isinstance(key, str) for key in header_rows)):
        raise ValueError("header names must be unique strings and may not be values")
    lengths = {len(column.get("values", ())) for column in columns}
    if len(lengths) != 1:
        raise ValueError("columns must have equal value counts")
    for column in columns:
        if "values" not in column or any(key not in column for key in header_rows):
            raise ValueError("missing header value")
        if any(not isinstance(value, str) for key in header_rows for value in (column[key],)):
            raise TypeError("headers must be strings")
        if any(not isinstance(value, str) for value in column["values"]):
            raise TypeError("cell values must be strings")
        cells = [column[key] for key in header_rows] + list(column["values"])
        if any("\n" in value or "\r" in value for value in cells):
            raise ValueError("table cells must be single-line strings")


def write_rst_table(columns, *, header_rows=("name",)):
    """Return a canonical fixed-width RST table."""
    _validate_columns(columns, header_rows)
    widths = [max([len(column[key]) for key in header_rows] +
                  [len(value) for value in column["values"]] + [1])
              for column in columns]
    separator = " ".join("=" * width for width in widths)
    lines = [separator]
    lines.extend(" ".join(column[key].ljust(width)
                          for column, width in zip(columns, widths)).rstrip()
                 for key in header_rows)
    lines.append(separator)
    row_count = len(columns[0]["values"])
    for row in range(row_count):
        lines.append(" ".join(column["values"][row].ljust(width)
                              for column, width in zip(columns, widths)).rstrip())
    lines.append(separator)
    return "\n".join(lines) + "\n"


def _widths(separator):
    parts = separator.split(" ")
    if not parts or any(not part or set(part) != {"="} for part in parts):
        raise ValueError("invalid separator")
    return [len(part) for part in parts]


def _cells(line, widths):
    padded = line.ljust(sum(widths) + len(widths) - 1)
    cells = []
    offset = 0
    for index, width in enumerate(widths):
        cells.append(padded[offset:offset + width].rstrip())
        offset += width
        if index + 1 < len(widths):
            if padded[offset:offset + 1] != " ":
                raise ValueError("invalid column boundary")
            offset += 1
    if padded[offset:].strip():
        raise ValueError("row is wider than the table")
    return cells


def read_rst_table(text, *, header_rows=("name",)):
    """Parse a canonical table produced by :func:`write_rst_table`."""
    if (not isinstance(text, str) or not isinstance(header_rows, tuple)
            or not header_rows or "name" not in header_rows
            or len(set(header_rows)) != len(header_rows)
            or "values" in header_rows
            or any(not isinstance(key, str) for key in header_rows)):
        raise ValueError("invalid table input")
    lines = text.splitlines()
    separator_index = 1 + len(header_rows)
    if len(lines) < separator_index + 2:
        raise ValueError("incomplete table")
    widths = _widths(lines[0])
    if lines[separator_index] != lines[0] or lines[-1] != lines[0]:
        raise ValueError("separator mismatch")
    columns = [{"values": []} for _ in widths]
    for row, key in enumerate(header_rows, start=1):
        for column, value in zip(columns, _cells(lines[row], widths)):
            column[key] = value
    for line in lines[separator_index + 1:-1]:
        if line == lines[0]:
            raise ValueError("unexpected separator in table body")
        for column, value in zip(columns, _cells(line, widths)):
            column["values"].append(value)
    return columns
