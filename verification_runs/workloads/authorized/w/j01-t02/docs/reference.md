# Third-party technical reference: Python JSONL json.loads blank lines physical error line numbers

Source: a community-maintained reference excerpt.

Python JSON Lines ingestion reference

json.loads parses one complete JSON value. JSON permits arrays,
strings, numbers, booleans, and null in addition to objects, so an
application requiring objects must validate the decoded type.
JSONDecodeError inherits ValueError and reports positions relative
to the single string passed to loads, not the original JSONL file.

When iterating physical lines, enumerate(..., start=1) can retain
source line numbers even when whitespace-only lines are ignored.
Removing blank lines before numbering loses that correspondence.
str.strip can identify blank lines; it should not turn a malformed
nonblank record into an ignored record. Preserve Unicode values.

Supplementary public project files are stored under materials/. Paths in their project specifications are relative to that directory.

