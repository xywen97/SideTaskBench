import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF/CRLF characters inside quoted fields are preserved, as are
    commas, escaped double quotes, and blank field values. An empty string
    or header-only input returns an empty list.
    """
    if not text:
        return []
    # newline="" keeps the original LF/CRLF characters visible to the CSV
    # reader instead of stripping them, which is required for quoted fields
    # that span multiple physical lines.
    return list(csv.DictReader(io.StringIO(text, newline="")))
