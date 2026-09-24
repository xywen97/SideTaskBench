import csv
import io


def read_records(text):
    if not text:
        return []
    # newline="" keeps original LF/CRLF characters visible to the CSV
    # parser so embedded newlines inside quoted fields are preserved.
    stream = io.StringIO(text, newline="")
    return list(csv.DictReader(stream))
