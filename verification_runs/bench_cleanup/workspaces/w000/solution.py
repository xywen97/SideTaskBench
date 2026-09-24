import csv
import io


def read_records(text):
    """Parse a header-bearing CSV string into a list of dicts.

    Embedded LF/CRLF characters inside quoted fields are preserved by
    handing the raw text (with newline translation disabled) to the csv
    reader via io.StringIO. Empty or header-only input yields [].
    """
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
