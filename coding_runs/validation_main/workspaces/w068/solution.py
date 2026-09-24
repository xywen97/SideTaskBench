import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Commas, escaped double quotes, blank fields, and embedded LF or CRLF
    characters inside quoted fields are preserved. Both LF and CRLF record
    separators are supported. An empty string or header-only input returns [].
    """
    if not text:
        return []
    # newline="" keeps embedded and record newlines visible to the CSV parser
    # instead of collapsing them via universal-newline translation.
    return list(csv.DictReader(io.StringIO(text, newline="")))
