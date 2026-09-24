import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dicts.

    Embedded LF/CRLF inside quoted fields are preserved. An empty string
    or a header-only input yields an empty list.
    """
    if not text:
        return []
    # newline="" keeps the original LF/CRLF characters visible to the csv
    # reader, which is required to preserve newlines inside quoted fields
    # and to correctly detect record separators.
    return list(csv.DictReader(io.StringIO(text, newline="")))
