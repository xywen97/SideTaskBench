import re
from datetime import datetime, timezone

# Strict contract:
#   YYYY-MM-DDTHH:MM:SS
#   optionally followed by "." and one to six fractional second digits
#   then either "Z" or a signed HH:MM UTC offset.
_TIMESTAMP_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})\Z"
)

_OFFSET_RE = re.compile(r"^(?P<sign>[+-])(?P<hours>\d{2}):(?P<minutes>\d{2})$")


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp and return it in UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` with optional one-to-six fractional
    second digits followed by either ``Z`` or a signed ``HH:MM`` offset.
    The returned :class:`datetime.datetime` is timezone-aware, normalized
    to :data:`datetime.timezone.utc`, and preserves the represented
    instant (including microseconds).

    Raises:
        ValueError: the value is not a string, does not match the required
            format, carries no timezone, or encodes an invalid date/time.
    """
    if not isinstance(value, str):
        raise ValueError(
            "timestamp must be a string, got %s" % type(value).__name__
        )

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError(
            "timestamp %r does not match "
            "YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM)" % (value,)
        )

    tz = match.group("tz")
    if tz != "Z":
        offset = _OFFSET_RE.match(tz)
        # The offset minute field must be a real minute; ``datetime``
        # otherwise silently rolls e.g. "+02:60" over to "+03:00".
        if int(offset.group("hours")) > 23 or int(offset.group("minutes")) > 59:
            raise ValueError("invalid UTC offset in %r" % (value,))
        normalized = value
    else:
        normalized = value[:-1] + "+00:00"

    # ``fromisoformat`` performs the calendar/time validation (month, day,
    # hour, minute, second, leap years, ...). Converting with ``astimezone``
    # shifts the instant to UTC instead of only relabelling the tzinfo.
    parsed = datetime.fromisoformat(normalized)
    return parsed.astimezone(timezone.utc)
