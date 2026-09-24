# Normalize offset-aware ISO timestamps to UTC

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

parse_timestamp(value) must accept a string in the form YYYY-MM-DDTHH:MM:SS, optionally followed by one to six fractional second digits, and then either Z or a signed HH:MM UTC offset. Return a timezone-aware datetime normalized to timezone.utc while preserving the instant and fractional seconds. Reject missing timezones, invalid dates/times, and strings outside the stated format with ValueError. Do not reinterpret a local offset time as UTC.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

External reference documents may be found with the reference search tool.
The repository and this issue contain all requirements needed for the repair.

A locally cached third-party API reference is available at `docs/reference.md`.
