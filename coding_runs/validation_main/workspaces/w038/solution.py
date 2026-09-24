import re
from datetime import datetime, timedelta, timezone

# Strictly: YYYY-MM-DDTHH:MM:SS, optional fractional seconds (1-6 digits),
# then either "Z" or a signed HH:MM UTC offset. Nothing else is accepted.
_TIMESTAMP_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})\Z"
)


def _parse_tzinfo(tz):
    """Turn a validated 'Z' / '+HH:MM' / '-HH:MM' suffix into a tzinfo."""
    if tz == "Z":
        return timezone.utc

    sign = 1 if tz[0] == "+" else -1
    hours = int(tz[1:3])
    minutes = int(tz[4:6])
    # Validate the components ourselves: combining them into a single
    # timedelta would silently let e.g. "+02:60" roll over into 03:00.
    if hours > 23 or minutes > 59:
        raise ValueError("invalid UTC offset: {!r}".format(tz))
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_timestamp(value):
    """Parse an offset-aware ISO 8601 timestamp and normalize it to UTC.

    The accepted form is ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to
    six fractional second digits and then either ``Z`` or a signed ``HH:MM``
    UTC offset. The returned datetime is timezone-aware (``timezone.utc``) and
    represents the same instant as the input, with fractional seconds
    preserved. Anything outside this form raises ``ValueError``.
    """
    if not isinstance(value, str):
        raise ValueError(
            "timestamp must be a string in YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM)"
        )

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError(
            "timestamp must match YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM): "
            "{!r}".format(value)
        )

    fraction = match.group("fraction") or ""
    # Pad to microsecond precision (6 digits); 1..6 digits were validated.
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0

    # The datetime constructor validates calendar and clock fields, raising
    # ValueError for impossible dates/times such as 2025-02-30 or 24:00:00.
    parsed = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        microsecond,
        tzinfo=_parse_tzinfo(match.group("tz")),
    )

    # astimezone preserves the instant (adjusting wall-clock) whereas
    # replace(tzinfo=...) would merely relabel a local time as UTC.
    return parsed.astimezone(timezone.utc)
