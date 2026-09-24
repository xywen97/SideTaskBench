import csv
import io


def read_records(text):
    # Use a StringIO stream with newline="" so the csv module sees the
    # original LF/CRLF characters and can decide whether a newline belongs
    # to a quoted field. Stripping line endings first (e.g. splitlines)
    # destroys embedded newlines inside quoted fields.
    return list(csv.DictReader(io.StringIO(text, newline="")))
