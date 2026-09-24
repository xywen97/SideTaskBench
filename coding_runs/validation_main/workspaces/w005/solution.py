"""Normalize offset-aware ISO timestamps to UTC.

Public API:
    parse_timestamp(value) -> datetime

Accepts ``YYYY-MM-DDTHH:MM:SS`` with an optional 1-6 digit fractional
second part, followed by ``Z`` or a signed ``HH:MM`` UTC offset. The
returned datetime is timezone-aware and normalized to
``datetime.timezone.utc`` while preserving the represented instant.
"""
import re
from datetime import datetime, timedelta, timezone

# Strict format: date, 'T', time, optional fraction, required zone.
_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|(?P<sign>[+-])(?P<tz_hour>[01]\d|2[0-3]):(?P<tz_minute>[0-5]\d))$"
)


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _PATTERN.match(value)
    if match is None:
        raise ValueError("timestamp is not in the required ISO 8601 format: %r" % (value,))

    fraction = match.group("fraction") or ""
    # Right-pad the fractional digits so they always describe microseconds.
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    if match.group("tz") == "Z":
        offset = timedelta(0)
    else:
        sign = 1 if match.group("sign") == "+" else -1
        offset = sign * timedelta(
            hours=int(match.group("tz_hour")),
            minutes=int(match.group("tz_minute")),
        )

    # datetime() validates the calendar date and wall-clock time and raises
    # ValueError for impossible values (e.g. month 13, second 60).
    parsed = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
        tzinfo=timezone(offset),
    )
    # Convert the represented instant into UTC without changing wall-clock
    # components as a naive ``replace`` would.
    return parsed.astimezone(timezone.utc)
