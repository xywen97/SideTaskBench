import re
from datetime import datetime, timedelta, timezone

_TIMESTAMP_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|(?P<sign>[+-])(?P<tz_hour>\d{2}):(?P<tz_minute>\d{2}))",
    re.ASCII,
)


def parse_timestamp(value):
    """Parse an ISO-8601 timestamp and normalize it to UTC.

    The accepted form is ``YYYY-MM-DDTHH:MM:SS`` followed optionally by one
    to six fractional second digits and then either ``Z`` or a signed
    ``HH:MM`` UTC offset.  A ``ValueError`` is raised for anything outside
    that format, including timestamps without a timezone.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the supported format: %r" % (value,))

    fraction = match.group("fraction") or ""
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # The datetime constructor raises ValueError for impossible dates/times
    # such as 2025-02-30, 2025-13-01, or 24:00:00.
    parsed = datetime(
        year=int(match.group("year")),
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")),
        microsecond=microsecond,
    )

    if match.group("tz") == "Z":
        tzinfo = timezone.utc
    else:
        tz_hour = int(match.group("tz_hour"))
        tz_minute = int(match.group("tz_minute"))
        if tz_hour > 23 or tz_minute > 59:
            raise ValueError("UTC offset out of range: %r" % (value,))
        offset = timedelta(hours=tz_hour, minutes=tz_minute)
        if match.group("sign") == "-":
            offset = -offset
        # timezone() validates that the offset is strictly less than 24 hours.
        tzinfo = timezone(offset)

    # Attach the parsed offset and convert the *instant* to UTC.  Using
    # astimezone (rather than replace) is essential: replace would relabel a
    # local wall-clock time as UTC without shifting it.
    return parsed.replace(tzinfo=tzinfo).astimezone(timezone.utc)
