import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded newlines (LF or CRLF) inside quoted fields are preserved.
    An empty string or header-only input returns [].
    """
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
