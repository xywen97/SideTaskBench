import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF/CRLF characters inside quoted fields are preserved. The
    input is supplied through ``io.StringIO`` with ``newline=""`` so that
    the csv module receives the original line endings (the same
    recommendation the standard library makes for opening files) rather
    than having them stripped by ``str.splitlines()``.
    """
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
