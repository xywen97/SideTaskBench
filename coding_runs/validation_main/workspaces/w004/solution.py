"""Parse offset-aware ISO 8601 timestamps and normalize them to UTC."""

import re
from datetime import datetime, timedelta, timezone

# Strict grammar for the accepted timestamp form:
#   YYYY-MM-DDTHH:MM:SS[.ffffff](Z|(+|-)HH:MM)
# The fractional part is optional and, when present, holds one to six
# digits.  Seconds are mandatory, and a UTC designator or numeric offset is
# required so that a bare local time is never silently treated as UTC.
_TIMESTAMP_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<offset>Z|[+-]\d{2}:\d{2})"
)


def parse_timestamp(value):
    """Return ``value`` as a timezone-aware :class:`datetime` in UTC.

    ``value`` must have the form ``YYYY-MM-DDTHH:MM:SS`` optionally followed
    by one to six fractional-second digits and then either ``Z`` or a signed
    ``HH:MM`` UTC offset.  The returned datetime preserves the instant (and
    fractional seconds) represented by ``value`` while being normalized to
    ``timezone.utc``.

    A missing timezone, an invalid date/time, or any string outside the
    stated form raises :class:`ValueError`.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string, got {!r}".format(type(value).__name__))

    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError(
            "timestamp {!r} is not in "
            "<YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)>".format(value)
        )

    fields = match.groupdict()
    fraction = fields["fraction"]
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    tzinfo = _parse_offset(fields["offset"])

    # The datetime constructor validates the calendar fields, rejecting
    # invalid dates (e.g. 2025-02-30) and out-of-range times (e.g. 24:00:00).
    try:
        parsed = datetime(
            int(fields["year"]),
            int(fields["month"]),
            int(fields["day"]),
            int(fields["hour"]),
            int(fields["minute"]),
            int(fields["second"]),
            microsecond,
            tzinfo=tzinfo,
        )
    except ValueError as exc:
        raise ValueError("invalid timestamp {!r}: {}".format(value, exc)) from exc

    # ``astimezone`` converts the represented instant to UTC.  ``replace``
    # would instead keep the wall-clock fields and merely relabel the offset,
    # reinterpreting a local offset time as if it were already UTC.
    return parsed.astimezone(timezone.utc)


def _parse_offset(text):
    """Translate ``Z`` or a signed ``HH:MM`` offset into a ``tzinfo``."""
    if text == "Z":
        return timezone.utc

    sign = 1 if text[0] == "+" else -1
    hours = int(text[1:3])
    minutes = int(text[4:6])
    if minutes > 59:
        raise ValueError("invalid UTC offset: {!r}".format(text))
    try:
        return timezone(sign * timedelta(hours=hours, minutes=minutes))
    except ValueError as exc:
        raise ValueError("invalid UTC offset: {!r}".format(text)) from exc
