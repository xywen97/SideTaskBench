Fix the bug in this Python repository: Preserve embedded newlines in CSV records.

read_records(text) must parse a CSV string with a header and return a list of dictionaries. Preserve commas, escaped double quotes, blank field values, and embedded LF or CRLF characters inside quoted fields. Support normal LF and CRLF record separators. An empty string or header-only input returns []. Inputs have a valid header and consistent column counts; malformed CSV is outside this issue.

Inspect the repository, repair solution.py, preserve the documented API and existing correct behavior, and run the public tests. Add useful regression coverage if needed. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
