import csv
import io


def read_records(text):
    # Provide the CSV parser with the raw text as a file-like stream. Using
    # io.StringIO with newline="" keeps embedded LF/CRLF characters inside
    # quoted fields intact instead of stripping them via str.splitlines().
    return list(csv.DictReader(io.StringIO(text, newline="")))
