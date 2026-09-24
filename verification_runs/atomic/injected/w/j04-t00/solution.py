import csv
import io


def read_records(text):
    return list(csv.DictReader(io.StringIO(text, newline="")))
