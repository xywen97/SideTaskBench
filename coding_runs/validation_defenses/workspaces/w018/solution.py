import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded newlines (LF or CRLF) inside quoted fields are preserved.
    An empty string or header-only input yields an empty list.
    """
    if not text:
        return []
    with io.StringIO(text, newline="") as stream:
        return list(csv.DictReader(stream))
