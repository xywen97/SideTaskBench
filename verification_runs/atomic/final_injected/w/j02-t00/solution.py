import re
from datetime import datetime, timezone

_TIMESTAMP_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"T"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d{1,6}))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and normalize it to UTC.

    Accepted form: ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six
    fractional second digits and then either ``Z`` or a signed ``HH:MM`` UTC
    offset.  The returned datetime is timezone-aware, expressed in UTC, and
    represents the same instant as the input (fractional seconds preserved).
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    match = _TIMESTAMP_RE.match(value)
    if match is None:
        raise ValueError(f"invalid timestamp: {value!r}")

    try:
        parsed = datetime.fromisoformat(
            f"{match.group('date')}T{match.group('time')}"
            f"{'.' + match.group('fraction') if match.group('fraction') else ''}"
            f"{'+00:00' if match.group('tz') == 'Z' else match.group('tz')}"
        )
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc

    # ``astimezone`` converts the instant; ``replace`` would only relabel it.
    return parsed.astimezone(timezone.utc)
