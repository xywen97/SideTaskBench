import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded newlines (LF or CRLF) inside quoted fields are preserved, as
    are commas, escaped double quotes, and blank field values. Both LF and
    CRLF record separators are supported. An empty or header-only input
    returns an empty list.
    """
    if not text:
        return []
    # newline="" keeps original line endings visible to the csv parser so
    # that newlines inside quoted fields are not stripped or translated.
    stream = io.StringIO(text, newline="")
    return list(csv.DictReader(stream))
