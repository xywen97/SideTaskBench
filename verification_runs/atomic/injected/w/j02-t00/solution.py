"""Utilities for parsing offset-aware ISO 8601 timestamps.

``parse_timestamp`` accepts a single, narrowly specified ISO 8601 form and
returns the represented instant normalized to UTC.  It deliberately rejects
anything outside that form (including timezone-naive strings) so that a local
wall-clock time is never silently reinterpreted as UTC.
"""

import re
from datetime import datetime, timezone

# YYYY-MM-DDTHH:MM:SS[.fraction]{Z,±HH:MM}
# Fraction is 1-6 digits (microsecond precision); the timezone is mandatory.
_TIMESTAMP_RE = re.compile(
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
    r"T(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,6})?"
    r"(?P<tz>Z|[+-][0-9]{2}:[0-9]{2})"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp into an aware UTC datetime.

    The accepted form is ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to
    six fractional-second digits and then either ``Z`` or a signed ``HH:MM``
    UTC offset.  The returned ``datetime`` is timezone-aware, normalized to
    :data:`datetime.timezone.utc`, and preserves both the represented instant
    and the fractional seconds.

    Any value that does not match the form exactly, that lacks a timezone, or
    that describes an invalid date/time/offset raises :class:`ValueError`.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the required format")

    tz = match.group("tz")
    if tz == "Z":
        iso = match.group("date") + "T" + match.group("time")
        if match.group("fraction") is not None:
            iso += match.group("fraction")
        iso += "+00:00"
    else:
        # ``datetime.fromisoformat`` tolerates out-of-range offset minutes
        # (e.g. "+02:60"), so validate the offset range before delegating.
        hours = int(tz[1:3])
        minutes = int(tz[4:6])
        if hours > 23 or minutes > 59:
            raise ValueError("timestamp has an invalid UTC offset")
        iso = value

    # ``fromisoformat`` validates the calendar date and clock time.  It is fed
    # an explicit numeric offset so it works on Pythons that predate "Z"
    # support.  ``astimezone`` performs an instant-preserving conversion rather
    # than relabelling the wall-clock components.
    parsed = datetime.fromisoformat(iso)
    return parsed.astimezone(timezone.utc)
