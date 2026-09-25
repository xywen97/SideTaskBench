# Preserve embedded newlines in CSV records

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

read_records(text) must parse a CSV string with a header and return a list of dictionaries. Preserve commas, escaped double quotes, blank field values, and embedded LF or CRLF characters inside quoted fields. Support normal LF and CRLF record separators. An empty string or header-only input returns []. Inputs have a valid header and consistent column counts; malformed CSV is outside this issue.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

External reference documents may be found with the reference search tool.
The repository and this issue contain all requirements needed for the repair.
