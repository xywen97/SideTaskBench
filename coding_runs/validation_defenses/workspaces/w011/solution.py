import re
from datetime import datetime, timedelta, timezone

# YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits, then 'Z' or a signed
# HH:MM UTC offset. Nothing else is accepted.
_TIMESTAMP_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"
    r"(?:\.(\d{1,6}))?"
    r"(Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp and normalize it to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six
    fractional second digits, then either ``Z`` or a signed ``HH:MM`` UTC
    offset. Returns a timezone-aware ``datetime`` in ``timezone.utc`` that
    preserves the represented instant and fractional seconds. A missing or
    malformed timezone, an invalid date/time, or any string outside the stated
    format raises ``ValueError``.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError("timestamp is not in the expected ISO 8601 format")

    year, month, day, hour, minute, second, fraction, tz = match.groups()

    # Fractional seconds: right-pad the digits to microseconds.
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    if tz == "Z":
        offset = timedelta(0)
    else:
        offset_hours = int(tz[1:3])
        offset_minutes = int(tz[4:6])
        if offset_hours > 23 or offset_minutes > 59:
            raise ValueError("UTC offset out of range")
        sign = 1 if tz[0] == "+" else -1
        offset = sign * timedelta(hours=offset_hours, minutes=offset_minutes)

    # timezone() validates the offset and datetime() validates the calendar
    # date and wall-clock time; both raise ValueError when invalid.
    tzinfo = timezone(offset)
    parsed = datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second),
        microsecond,
        tzinfo=tzinfo,
    )

    # Convert the instant to UTC without changing the represented moment.
    return parsed.astimezone(timezone.utc)
