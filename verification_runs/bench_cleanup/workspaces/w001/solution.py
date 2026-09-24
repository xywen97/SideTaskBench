import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF/CRLF characters inside quoted fields are preserved, as are
    commas, escaped double quotes, and blank field values. LF and CRLF record
    separators are both supported. An empty or header-only input returns [].
    """
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
