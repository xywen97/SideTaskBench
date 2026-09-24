import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Commas, escaped double quotes, blank fields, and embedded LF/CRLF
    characters inside quoted fields are preserved. Both LF and CRLF record
    separators are supported. An empty or header-only input yields [].
    """
    if not text:
        return []
    # newline="" disables universal-newline translation so the csv parser
    # sees the original record separators and keeps newlines that occur
    # inside quoted fields intact.
    stream = io.StringIO(text, newline="")
    return list(csv.DictReader(stream))
