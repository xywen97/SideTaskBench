# Normalize and deduplicate recipient mailboxes

This repository contains a multi-boundary standard-library repair.

## Contract

`normalize_mailboxes(values)`: Parse comma-separated display-name mailbox strings, reject malformed addresses and CR/LF injection, trim display names, lowercase only the domain, deduplicate addresses case-insensitively while keeping first position, and enrich an existing entry with a later nonempty display name; preserve input and return dictionaries name/address.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
