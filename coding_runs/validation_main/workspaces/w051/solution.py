import csv
import io


def read_records(text):
    """Parse an in-memory CSV string into a list of dictionaries.

    Passing newline="" to StringIO keeps LF and CRLF sequences intact for
    the CSV parser, so record separators are recognized without stripping
    newline characters that belong to quoted fields.
    """
    return list(csv.DictReader(io.StringIO(text, newline="")))
