import re
from datetime import datetime, timedelta, timezone

# Strictly match one of the two documented forms:
#   YYYY-MM-DDTHH:MM:SS[.fraction]{,6}Z
#   YYYY-MM-DDTHH:MM:SS[.fraction]{,6}(+|-)HH:MM
_ISO_PATTERN = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.(?P<fraction>[0-9]{1,6}))?"
    r"(?P<tz>Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


def _parse_timezone(text):
    """Return a tzinfo for the matched ``Z`` or ``+/-HH:MM`` suffix."""
    if text == "Z":
        return timezone.utc

    sign = 1 if text[0] == "+" else -1
    hours = int(text[1:3])
    minutes = int(text[4:6])
    if minutes >= 60:
        raise ValueError("offset minutes must be in 00..59")
    delta = timedelta(hours=hours, minutes=minutes)
    # timezone() rejects offsets >= 24h, which ValueError surfaces correctly.
    return timezone(sign * delta)


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _ISO_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("timestamp is not in the accepted ISO-8601 format")

    parts = match.groupdict()
    fraction = parts["fraction"] or ""
    microsecond = int(fraction.ljust(6, "0"))

    try:
        naive = datetime(
            int(parts["year"]),
            int(parts["month"]),
            int(parts["day"]),
            int(parts["hour"]),
            int(parts["minute"]),
            int(parts["second"]),
            microsecond,
        )
        tzinfo = _parse_timezone(parts["tz"])
    except ValueError as exc:
        raise ValueError(f"invalid timestamp {value!r}: {exc}") from exc

    # Interpret the parsed components in the stated offset, then convert the
    # resulting instant to UTC. astimezone (not replace) adjusts the wall clock.
    aware = naive.replace(tzinfo=tzinfo)
    return aware.astimezone(timezone.utc)
