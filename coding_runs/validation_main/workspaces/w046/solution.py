import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF or CRLF characters inside quoted fields are preserved.
    An empty string or header-only input returns [].
    """
    return list(csv.DictReader(io.StringIO(text, newline="")))
