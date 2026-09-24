"""Parse offset-aware ISO-8601 timestamps and normalize them to UTC."""

import re
from datetime import datetime, timedelta, timezone

# YYYY-MM-DDTHH:MM:SS[.ffffff] followed by either "Z" or a signed HH:MM offset.
_TIMESTAMP_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<offset>Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value):
    """Return a UTC-aware ``datetime`` for an offset-aware ISO timestamp.

    ``value`` must be ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to
    six fractional second digits and then either ``Z`` or a signed ``HH:MM``
    UTC offset. The instant is preserved and normalized to
    ``timezone.utc``; a local offset is converted, never relabeled.

    A :class:`ValueError` is raised for missing timezones, invalid
    dates/times, and strings outside the accepted format.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError("timestamp is not a valid ISO-8601 string: %r" % (value,))

    fraction = match.group("fraction")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    offset_token = match.group("offset")
    if offset_token == "Z":
        tzinfo = timezone.utc
    else:
        sign = 1 if offset_token[0] == "+" else -1
        offset_hours = int(offset_token[1:3])
        offset_minutes = int(offset_token[4:6])
        if offset_hours > 23 or offset_minutes > 59:
            raise ValueError("timestamp has an invalid UTC offset: %r" % (value,))
        tzinfo = timezone(sign * timedelta(hours=offset_hours, minutes=offset_minutes))

    # Constructing the datetime validates the calendar/clock fields and
    # raises ValueError for impossible dates and times.
    parsed = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
        tzinfo=tzinfo,
    )

    # astimezone shifts the wall clock to preserve the instant; replace()
    # would relabel the same wall clock and corrupt offset-bearing input.
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError:
        # The instant is valid but falls outside the representable range.
        raise ValueError("timestamp is out of range: %r" % (value,))
