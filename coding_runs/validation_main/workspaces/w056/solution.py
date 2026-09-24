import csv
import io


def read_records(text):
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text, newline="")))
