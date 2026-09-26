# Resolve layered typed configuration without mutating inputs

This repository contains a multi-boundary standard-library repair.

## Contract

`resolve_settings(layers)`: Apply layers in order over fixed defaults timeout=5.0, retries=3, enabled=True, tags=[]; parse strict strings and native values; None resets a key to its default; tags accept a comma string or iterable, trim and deduplicate in order; reject unknown keys, bool-as-number, nonfinite timeout, and invalid values; return fresh data without mutation.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
