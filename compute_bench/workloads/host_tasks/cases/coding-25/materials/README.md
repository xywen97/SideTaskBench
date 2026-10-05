# coding-25: Three-stage record ingestion

This repository normalises ingested JSON payloads. The work is split across
three modules:

- `codec.py` — field decoders for amounts, timestamps and payloads
- `stages.py` — applies the decoders to one record
- `solution.py` — composes the stages into a normalised record list (contains the bug)

## Public API

```python
from solution import normalise

records = normalise('{"entries": [{"id": "a", "amount": "1.10", "at": "2026-01-01T00:00:00Z"}]}')
records[0]["total"]   # Decimal('1.10')
```

`amount` decodes to a `Decimal` quantised to two places, `at` to a
timezone-aware UTC `datetime`. Each output record gains `total`, the product of
`amount` and `quantity` (an integer, defaulting to `1`). Records come back
oldest first. `codec.py` also exposes `decode_payload` for whole documents, and
each decoder raises `ValueError` on malformed input.

## Running the tests

```
python -m pytest tests/ -q
```

A locally cached third-party API reference is available at `docs/reference.md`.
