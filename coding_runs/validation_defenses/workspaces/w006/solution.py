import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded LF or CRLF characters inside quoted fields are preserved as-is,
    along with commas, escaped double quotes, and blank field values.  Both LF
    and CRLF record separators are supported.  An empty string or a
    header-only input returns an empty list.
    """
    if not text:
        return []
    # newline="" disables universal-newline translation so the csv module can
    # see the original line endings and correctly keep newlines that appear
    # inside quoted fields.
    return list(csv.DictReader(io.StringIO(text, newline="")))
