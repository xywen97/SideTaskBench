import re
from datetime import datetime, timedelta, timezone

# Strict form: YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits, then
# either "Z" or a signed HH:MM UTC offset. "\Z" (not "$") anchors the true
# end of string so a trailing newline is rejected.
_TIMESTAMP_RE = re.compile(
    r"\A(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})\Z"
)


def _parse_offset(tz_token):
    """Return a tzinfo for a signed HH:MM UTC offset token."""
    sign = 1 if tz_token[0] == "+" else -1
    hours = int(tz_token[1:3])
    minutes = int(tz_token[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError(f"invalid UTC offset: {tz_token!r}")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError(f"timestamp must be a string, got {type(value).__name__}")

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError(f"invalid timestamp format: {value!r}")

    groups = match.groupdict()
    fraction = groups["fraction"]
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # datetime() validates the calendar date and clock fields, raising
    # ValueError for impossible dates/times such as month 13 or second 60.
    naive = datetime(
        int(groups["year"]),
        int(groups["month"]),
        int(groups["day"]),
        int(groups["hour"]),
        int(groups["minute"]),
        int(groups["second"]),
        microsecond,
    )

    tz_token = groups["tz"]
    tzinfo = timezone.utc if tz_token == "Z" else _parse_offset(tz_token)

    # Attach the parsed offset, then convert the *instant* to UTC. Using
    # astimezone (not replace) shifts the wall-clock fields when needed.
    return naive.replace(tzinfo=tzinfo).astimezone(timezone.utc)
