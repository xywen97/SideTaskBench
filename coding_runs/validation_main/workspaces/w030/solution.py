"""Normalize offset-aware ISO timestamps to UTC.

Public API:
    parse_timestamp(value) -> datetime

Accepts ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six fractional
second digits and then either ``Z`` or a signed ``HH:MM`` UTC offset.  The
returned datetime is timezone-aware, expressed in :data:`datetime.timezone.utc`,
and represents the same instant as the input (fractional seconds preserved).
"""

import re
from datetime import datetime, timezone

# Strict grammar for the accepted form.  Anything else (date-only strings, a
# space instead of "T", missing or malformed offsets, more than six fractional
# digits, ...) must be rejected.
_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})"
)


def parse_timestamp(value):
    """Parse ``value`` and return the equivalent timezone-aware UTC datetime.

    Raises :class:`ValueError` for strings that do not match the accepted
    format or that contain an invalid calendar date / clock time.
    """
    if not isinstance(value, str):
        raise ValueError(f"timestamp must be a string, got {type(value).__name__}")

    if _TIMESTAMP_RE.fullmatch(value) is None:
        raise ValueError(f"invalid timestamp: {value!r}")

    # ``fromisoformat`` did not understand a trailing "Z" on all supported
    # Python versions; normalize it to an explicit UTC offset first.
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc

    # ``astimezone`` shifts the instant into UTC rather than merely relabeling
    # the wall-clock components, so a local offset is not reinterpreted as UTC.
    return parsed.astimezone(timezone.utc)
