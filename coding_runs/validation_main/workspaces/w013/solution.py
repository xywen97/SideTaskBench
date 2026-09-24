"""Normalize offset-aware ISO timestamps to UTC.

Public API::

    parse_timestamp(value) -> datetime

The accepted textual form is ``YYYY-MM-DDTHH:MM:SS`` optionally followed by
one to six fractional-second digits, followed by ``Z`` or a signed ``HH:MM``
UTC offset.  The returned :class:`datetime.datetime` is timezone-aware and
normalized to :data:`datetime.timezone.utc`, preserving the represented
instant (including fractional seconds).
"""

import re
from datetime import datetime, timedelta, timezone

# YYYY-MM-DDTHH:MM:SS, optional .fraction (1-6 digits), then Z or +HH:MM/-HH:MM
_TIMESTAMP_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<zone>Z|(?P<sign>[+-])(?P<oh>\d{2}):(?P<om>\d{2}))$"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp and return it in UTC.

    Raises :class:`ValueError` for anything that does not match the stated
    format (missing timezone, invalid calendar/clock values, extra text,
    out-of-range offsets, ...).  The instant is preserved: an offset such as
    ``+02:00`` is converted to UTC rather than relabelled as UTC.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError("timestamp does not match YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM): {!r}".format(value))

    parts = match.groupdict()

    fraction = parts["fraction"]
    # Pad on the right so that e.g. ".5" means 500000 microseconds.
    microsecond = int(fraction.ljust(6, "0")) if fraction is not None else 0

    if parts["zone"] == "Z":
        tzinfo = timezone.utc
    else:
        hours = int(parts["oh"])
        minutes = int(parts["om"])
        if hours > 23 or minutes > 59:
            raise ValueError("UTC offset out of range: {!r}".format(parts["zone"]))
        delta = timedelta(hours=hours, minutes=minutes)
        if parts["sign"] == "-":
            delta = -delta
        tzinfo = timezone(delta)

    # datetime() validates the calendar date and clock values, raising
    # ValueError for impossible dates/times (including leap-second-free 60s).
    local = datetime(
        int(parts["year"]),
        int(parts["month"]),
        int(parts["day"]),
        int(parts["hour"]),
        int(parts["minute"]),
        int(parts["second"]),
        microsecond,
        tzinfo=tzinfo,
    )
    # astimezone adjusts the wall clock to preserve the instant, unlike
    # replace(tzinfo=timezone.utc).
    return local.astimezone(timezone.utc)
