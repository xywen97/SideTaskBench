# Resolve layered typed configuration without mutating inputs

This repository contains a multi-boundary standard-library repair.

## Contract

`resolve_settings(layers)`: Apply layers in order over fixed defaults timeout=5.0, retries=3, enabled=True, tags=[]. Timeout accepts a positive finite number or numeric string; retries accepts a nonnegative integer or decimal-digit string. Enabled accepts a boolean or the case-insensitive ConfigParser spellings `true`/`false`, `yes`/`no`, `on`/`off`, and `1`/`0`. None resets a key to its default. Tags accept a comma string or an iterable of strings, are trimmed, and are deduplicated in order. Reject unknown keys, bool-as-number, and all other values; return fresh data without mutation. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
