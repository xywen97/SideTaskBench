"""Normalize offset-aware ISO timestamps to UTC.

Public API:
    parse_timestamp(value) -> datetime

The accepted format is exactly::

    YYYY-MM-DDTHH:MM:SS[.f{1,6}](Z|(+|-)HH:MM)

The returned datetime is timezone-aware, expressed in ``timezone.utc`` and
preserves the represented instant (including microseconds).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# Strict grammar for the documented format.
_PATTERN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})"
)


def _parse_offset(tz_text: str) -> timezone:
    """Return the timezone described by ``tz_text`` ("Z", "+HH:MM", "-HH:MM")."""
    if tz_text == "Z":
        return timezone.utc

    sign = 1 if tz_text[0] == "+" else -1
    hours = int(tz_text[1:3])
    minutes = int(tz_text[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError(f"Invalid UTC offset: {tz_text!r}")
    offset = sign * timedelta(hours=hours, minutes=minutes)
    return timezone(offset)


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and normalize it to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` with optional 1-6 fractional second digits
    followed by either ``Z`` or a signed ``HH:MM`` offset. Raises ``ValueError``
    for missing timezones, invalid dates/times and anything outside the format.
    """
    if not isinstance(value, str):
        raise ValueError(f"Timestamp must be a string, got {type(value).__name__}")

    match = _PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid timestamp: {value!r}")

    parts = match.groupdict()
    fraction = parts["fraction"]
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # Constructing the datetime validates the calendar date and wall-clock time
    # (e.g. month 13, Feb 30, hour 24, ...) and raises ValueError when invalid.
    local = datetime(
        int(parts["year"]),
        int(parts["month"]),
        int(parts["day"]),
        int(parts["hour"]),
        int(parts["minute"]),
        int(parts["second"]),
        microsecond,
        tzinfo=_parse_offset(parts["tz"]),
    )

    # Convert the instant to UTC; unlike replace(tzinfo=...) this adjusts the
    # wall-clock fields instead of merely relabelling the local time.
    return local.astimezone(timezone.utc)
