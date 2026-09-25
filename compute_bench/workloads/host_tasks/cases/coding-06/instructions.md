Fix the bug in this Python repository: Normalize offset-aware ISO timestamps to UTC.

parse_timestamp(value) must accept a string in the form YYYY-MM-DDTHH:MM:SS, optionally followed by one to six fractional second digits, and then either Z or a signed HH:MM UTC offset. Return a timezone-aware datetime normalized to timezone.utc while preserving the instant and fractional seconds. Reject missing timezones, invalid dates/times, and strings outside the stated format with ValueError. Do not reinterpret a local offset time as UTC.

Inspect the repository, repair solution.py, preserve the documented API and existing correct behavior, and run the public tests. Add useful regression coverage if needed. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
