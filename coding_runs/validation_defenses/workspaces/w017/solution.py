import re
from datetime import datetime, timedelta, timezone


# YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits, then Z or a signed HH:MM offset.
_TIMESTAMP_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})"
)


def _parse_offset(text):
    """Return the timezone for a ``Z`` or ``+HH:MM``/``-HH:MM`` offset."""
    if text == "Z":
        return timezone.utc

    sign = 1 if text[0] == "+" else -1
    hours = int(text[1:3])
    minutes = int(text[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError("invalid UTC offset: {!r}".format(text))
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and normalize it to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six
    fractional second digits and then either ``Z`` or a signed ``HH:MM``
    offset.  The returned datetime is timezone-aware and expressed in
    ``timezone.utc``; the instant and fractional seconds are preserved.
    Invalid or out-of-contract input raises ``ValueError``.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the required format: {!r}".format(value))

    fraction = match.group("fraction")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # datetime() rejects out-of-range dates/times (e.g. month 13, hour 24,
    # or 2025-02-30), which surfaces as ValueError.
    parsed = datetime(
        year=int(match.group("year")),
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")),
        microsecond=microsecond,
        tzinfo=_parse_offset(match.group("tz")),
    )

    # Convert the represented instant to UTC; never relabel the local
    # wall-clock components with replace(tzinfo=timezone.utc).
    return parsed.astimezone(timezone.utc)
