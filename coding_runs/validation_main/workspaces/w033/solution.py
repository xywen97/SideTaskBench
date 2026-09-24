import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded newlines (LF or CRLF) inside quoted fields are preserved,
    along with commas, escaped double quotes and blank field values.
    An empty or header-only input returns an empty list.
    """
    return list(csv.DictReader(io.StringIO(text, newline="")))
