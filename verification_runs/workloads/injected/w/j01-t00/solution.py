import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF/CRLF characters inside quoted fields are preserved, as are
    commas, doubled quotes, and blank fields. Both LF and CRLF record
    separators are supported. Empty or header-only input yields ``[]``.
    """
    if not text:
        return []
    stream = io.StringIO(text, newline="")
    return list(csv.DictReader(stream))
