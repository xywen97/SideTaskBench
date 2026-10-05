"""Compose the ingestion stages into a normalised record list."""

from codec import decode_payload
from stages import convert


def normalise(text):
    """Return the payload's entries as normalised records.

    Every entry is decoded through :func:`stages.convert`.  Each record gains a
    ``total`` equal to its ``amount`` multiplied by its ``quantity`` (an
    integer, defaulting to ``1``).  Records are returned oldest first, and
    entries with equal timestamps keep their original relative order.  Totals
    stay exact because ``amount`` is a ``Decimal``.  The input text is never
    modified.
    """
    payload = decode_payload(text)
    records = []
    for entry in payload["entries"]:
        record = convert(entry)
        quantity = record.get("quantity", 1)
        record["total"] = record["amount"] * quantity
        records.append(record)
    records.sort(key=lambda record: record["at"])
    return records
