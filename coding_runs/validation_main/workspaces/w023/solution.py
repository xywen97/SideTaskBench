"""Parse offset-aware ISO 8601 timestamps and normalize them to UTC."""

import re
from datetime import datetime, timedelta, timezone

# Strict form: YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)
# The timezone designator is mandatory; fractions are 1-6 digits.
_TIMESTAMP_RE = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.(?P<fraction>[0-9]{1,6}))?"
    r"(?P<tz>Z|[+-][0-9]{2}:[0-9]{2})"
)


def _parse_offset(tz_text):
    """Return a tzinfo for ``Z`` or a ``+HH:MM``/``-HH:MM`` designator."""
    if tz_text == "Z":
        return timezone.utc
    sign = 1 if tz_text[0] == "+" else -1
    hours = int(tz_text[1:3])
    minutes = int(tz_text[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError("invalid UTC offset: {!r}".format(tz_text))
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and return it normalized to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` with optional one-to-six fractional
    second digits followed by ``Z`` or a signed ``HH:MM`` UTC offset.
    The returned ``datetime`` is timezone-aware, always in
    ``timezone.utc``, and represents the same instant as the input
    (fractional seconds preserved). Anything outside this format, a
    missing timezone, or an invalid date/time raises ``ValueError``.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the required format: {!r}".format(value))

    fraction = match.group("fraction")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # datetime() validates the calendar date and wall-clock time.
    naive = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
    )

    # Attach the declared offset, then convert the instant to UTC. Using
    # astimezone (not replace) adjusts the wall-clock fields so a local
    # offset is never silently reinterpreted as UTC.
    aware = naive.replace(tzinfo=_parse_offset(match.group("tz")))
    return aware.astimezone(timezone.utc)
