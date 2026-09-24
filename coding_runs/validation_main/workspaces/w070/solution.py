"""Timestamp parsing utilities."""

import re
from datetime import datetime, timedelta, timezone

_ISO_TIMESTAMP_RE = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.(?P<fraction>[0-9]{1,6}))?"
    r"(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})"
)


def _parse_offset(value):
    if value == "Z":
        return timezone.utc

    sign = 1 if value[0] == "+" else -1
    hours = int(value[1:3])
    minutes = int(value[4:6])

    # datetime.timezone only accepts offsets strictly between -24 and +24
    # hours, and a real UTC offset cannot contain 60 minutes.
    if hours > 23 or minutes > 59:
        raise ValueError("invalid UTC offset: {!r}".format(value))

    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    """Parse an ISO timestamp and return it normalized to UTC.

    The accepted form is ``YYYY-MM-DDTHH:MM:SS`` with an optional
    ``.fraction`` of one to six digits, followed by either ``Z`` or a
    signed ``HH:MM`` offset.  The returned value is timezone-aware and
    always has ``tzinfo=timezone.utc``.
    """

    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _ISO_TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the required ISO format: {!r}".format(value))

    fraction = match.group("fraction")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # The datetime constructor validates calendar dates and clock times.
    local_dt = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
    )

    offset = _parse_offset(match.group("offset"))
    aware_dt = local_dt.replace(tzinfo=offset)

    # astimezone changes the wall-clock representation to the same instant
    # in UTC; replace(tzinfo=timezone.utc) would incorrectly relabel it.
    try:
        return aware_dt.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("timestamp cannot be represented in UTC") from exc
