# Normalize and deduplicate recipient mailboxes

This repository contains a multi-boundary standard-library repair.

## Contract

`normalize_mailboxes(values)`: Parse comma-separated display-name mailbox strings and reject CR/LF injection. An address must contain exactly one `@`, a valid local part, and one or more valid domain labels; single-label local domains are accepted. Trim display names, lowercase only the domain, deduplicate addresses case-insensitively while keeping first position, and enrich an existing entry with a later nonempty display name; preserve input and return dictionaries name/address. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
