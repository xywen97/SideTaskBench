import csv
import io


def read_records(text):
    # Feed the raw text to the CSV parser without pre-splitting lines.
    # newline="" keeps original LF/CRLF characters visible so the parser
    # can distinguish record separators from newlines embedded in quoted
    # fields (and preserve commas, escaped quotes, and blank fields).
    return list(csv.DictReader(io.StringIO(text, newline="")))
