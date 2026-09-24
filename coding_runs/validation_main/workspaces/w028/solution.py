import csv
import io


def read_records(text):
    """Parse a CSV string with a header into a list of dictionaries.

    Embedded newlines inside quoted fields are preserved, so the input is
    handed to the csv module as an in-memory stream with newline="" rather
    than being split into physical lines first.
    """
    return list(csv.DictReader(io.StringIO(text, newline="")))
