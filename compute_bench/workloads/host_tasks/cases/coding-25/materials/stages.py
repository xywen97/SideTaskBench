"""Field-level conversion for one ingested record."""

from codec import parse_amount, parse_timestamp


CONVERTERS = {"amount": parse_amount, "at": parse_timestamp}


def convert(record):
    """Return a copy of *record* with known fields decoded.

    Fields not listed in :data:`CONVERTERS` are preserved unchanged.  The input
    mapping is never mutated.  Errors from a decoder propagate unchanged.
    """
    converted = dict(record)
    for field, decoder in CONVERTERS.items():
        if field in converted:
            converted[field] = decoder(converted[field])
    return converted
