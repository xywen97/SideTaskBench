import csv

def read_records(text):
    return list(csv.DictReader(text.splitlines()))
