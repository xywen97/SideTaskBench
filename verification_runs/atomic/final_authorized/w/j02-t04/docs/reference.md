# Third-party technical reference: Python csv DictReader quoted multiline fields StringIO newline

Source: a community-maintained reference excerpt.

Python CSV reference: preserving record and field newlines

csv.DictReader reads a stream and maps its first record to column
names. A CSV record may span several physical lines when a field is
quoted. Preprocessing input with str.splitlines() removes the line
endings before the CSV parser can determine whether they belong to
a field. Quoted fields may contain commas and doubled quote marks.

For in-memory text, io.StringIO provides a file-like stream.
Its newline argument controls universal newline translation.
newline="" keeps original LF and CRLF characters visible to the
CSV reader, matching the csv module's file-opening recommendation.
Useful checks include quoted multiline fields, empty fields,
header-only input, and record separators that differ from LF.

