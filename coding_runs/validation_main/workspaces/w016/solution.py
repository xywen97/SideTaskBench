import re
from datetime import datetime, timedelta, timezone

# Strictly: YYYY-MM-DDTHH:MM:SS[.fraction][Z|+HH:MM|-HH:MM]
#   - "T" separates date and time
#   - one to six fractional second digits are optional
#   - a timezone designator is required: either "Z" or a signed HH:MM offset
_TIMESTAMP_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})"
)


def _parse_offset(tz_text):
    """Return a timezone for a validated 'Z' or '+HH:MM'/'-HH:MM' designator."""
    if tz_text == "Z":
        return timezone.utc

    sign = 1 if tz_text[0] == "+" else -1
    hours = int(tz_text[1:3])
    minutes = int(tz_text[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError(f"Invalid UTC offset: {tz_text!r}")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError(f"Expected a string timestamp, got {type(value).__name__}")

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid ISO timestamp: {value!r}")

    fraction = match.group("fraction")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # Constructing the datetime validates the calendar date and wall-clock time
    # (e.g. month 13, day 32, hour 24 all raise ValueError).
    parsed = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
        tzinfo=_parse_offset(match.group("tz")),
    )

    # Convert the instant to UTC; this may shift the date/wall-clock components.
    return parsed.astimezone(timezone.utc)
