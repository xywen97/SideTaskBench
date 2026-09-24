"""Utilities for parsing offset-aware ISO 8601 timestamps."""

import re
from datetime import datetime, timezone

# Strict shape: YYYY-MM-DDTHH:MM:SS, optional 1-6 fractional digits, then
# either "Z" or a signed HH:MM offset (hours 00-23, minutes 00-59).
_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T"
    r"\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)"
)


def parse_timestamp(value):
    """Parse an offset-aware ISO timestamp and normalize it to UTC.

    Accepts ``YYYY-MM-DDTHH:MM:SS`` optionally followed by one to six
    fractional second digits and then either ``Z`` or a signed ``HH:MM``
    offset.  Returns a timezone-aware :class:`datetime.datetime` whose
    ``tzinfo`` is :data:`datetime.timezone.utc`, preserving the instant and
    any fractional seconds.

    A missing timezone, an invalid date/time, or any string outside the
    stated format raises :class:`ValueError`.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    if _TIMESTAMP_RE.fullmatch(value) is None:
        raise ValueError("timestamp is not a valid ISO 8601 offset timestamp: {!r}".format(value))

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        # Well-shaped but calendrically invalid (e.g. month 13, day 32).
        raise ValueError("invalid timestamp: {!r}".format(value)) from exc

    # Re-anchor to the absolute instant in UTC; this is what makes e.g.
    # "+02:00" shift the wall clock instead of being reinterpreted as if it
    # were already UTC.
    return parsed.astimezone(timezone.utc)
