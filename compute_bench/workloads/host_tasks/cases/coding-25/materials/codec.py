"""Low-level field decoders for ingested records."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from datetime import datetime, timezone


AMOUNT_PLACES = Decimal("0.01")


def parse_amount(text):
    """Return *text* as a ``Decimal`` quantised to two places, half-up.

    Raises ``ValueError`` for malformed input and for non-finite values such as
    ``"NaN"`` or ``"Infinity"``.  The result is always a ``Decimal``; callers
    that need exact arithmetic must not convert it to ``float``.
    """
    if not isinstance(text, str):
        raise ValueError("amount must be a string")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError("malformed amount: " + text) from None
    if not value.is_finite():
        raise ValueError("amount must be finite: " + text)
    return value.quantize(AMOUNT_PLACES, rounding=ROUND_HALF_UP)


def parse_timestamp(text):
    """Return *text* as a timezone-aware UTC ``datetime``.

    Accepts ISO-8601 spellings, including a trailing ``Z``.  Raises
    ``ValueError`` for malformed or naive input; an absent offset is an error
    because it makes ordering ambiguous.
    """
    if not isinstance(text, str):
        raise ValueError("timestamp must be a string")
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        raise ValueError("malformed timestamp: " + text) from None
    if parsed.tzinfo is None:
        raise ValueError("timestamp needs an explicit offset: " + text)
    return parsed.astimezone(timezone.utc)


def decode_payload(text):
    """Return the parsed JSON object in *text*.

    Raises ``ValueError`` unless the document is a JSON object with an
    ``"entries"`` list.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("malformed payload: " + str(error)) from None
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if not isinstance(payload.get("entries"), list):
        raise ValueError("payload needs an entries list")
    return payload
