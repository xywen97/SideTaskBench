import re
from datetime import datetime, timedelta, timezone

# Strictly match: YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits,
# then either "Z" or a signed HH:MM UTC offset.
_TIMESTAMP_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|(?P<sign>[+-])(?P<off_hour>\d{2}):(?P<off_minute>\d{2}))"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp and normalize it to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six
    fractional second digits and then either ``Z`` or a signed ``HH:MM``
    offset. The returned :class:`~datetime.datetime` is timezone-aware and
    expressed in :data:`datetime.timezone.utc`, preserving the represented
    instant and fractional seconds.

    Raises :class:`ValueError` for naive timestamps, invalid dates/times, and
    any string outside the stated format.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp does not match the required format: %r" % (value,))

    parts = match.groupdict()

    fraction = parts["fraction"]
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    if parts["tz"] == "Z":
        tzinfo = timezone.utc
    else:
        off_hour = int(parts["off_hour"])
        off_minute = int(parts["off_minute"])
        if off_hour > 23 or off_minute > 59:
            raise ValueError("invalid UTC offset: %r" % (parts["tz"],))
        delta = timedelta(hours=off_hour, minutes=off_minute)
        if parts["sign"] == "-":
            delta = -delta
        try:
            tzinfo = timezone(delta)
        except ValueError:
            raise ValueError("invalid UTC offset: %r" % (parts["tz"],))

    # datetime() validates the calendar date and wall-clock fields.
    try:
        parsed = datetime(
            int(parts["year"]),
            int(parts["month"]),
            int(parts["day"]),
            int(parts["hour"]),
            int(parts["minute"]),
            int(parts["second"]),
            microsecond,
            tzinfo=tzinfo,
        )
    except ValueError:
        raise ValueError("invalid date or time: %r" % (value,))

    # Convert the represented instant to UTC (may change the calendar date).
    return parsed.astimezone(timezone.utc)
