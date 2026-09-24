import csv
import io


def read_records(text):
    """Parse *text* as CSV with a header, returning a list of dicts.

    Embedded LF/CRLF characters inside quoted fields are preserved.
    """
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
