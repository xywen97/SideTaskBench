import re
from datetime import datetime, timezone

# YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits, then Z or a real
# signed HH:MM UTC offset (00-23 hours, 00-59 minutes).
_OFFSET = r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?"
    + _OFFSET
    + r"$"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and normalize it to UTC.

    Returns a timezone-aware ``datetime`` in ``timezone.utc`` preserving the
    instant and fractional seconds. Raises ``ValueError`` for anything outside
    the documented format, including timestamps without a timezone.
    """
    if not isinstance(value, str) or _PATTERN.match(value) is None:
        raise ValueError(
            "timestamp must match YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM)"
        )

    # ``fromisoformat`` only learned to accept a trailing "Z" in Python 3.11;
    # normalize it to an explicit offset for portability.
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc

    if parsed.tzinfo is None:
        raise ValueError(f"timestamp is missing a timezone: {value!r}")

    # ``astimezone`` converts the instant; ``replace`` would only relabel it.
    return parsed.astimezone(timezone.utc)
