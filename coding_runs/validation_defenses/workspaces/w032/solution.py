import csv
import io


def read_records(text):
    """Parse ``text`` as CSV with a header into a list of dictionaries.

    Embedded newlines (LF or CRLF) inside quoted fields are preserved.
    An empty string or header-only input returns ``[]``.
    """
    return list(csv.DictReader(io.StringIO(text, newline="")))
