# Merge HTTP headers without forwarding hop-by-hop state

This repository contains a multi-boundary standard-library repair.

## Contract

`merge_headers(base, updates)`: Both inputs are ordered iterables of `(name, value)` string pairs. Validate header names and values, normalize names to lowercase and trim optional whitespace, remove standard hop-by-hop fields plus fields named by Connection, append ordinary repeated fields, replace singleton host/content-length/content-type fields using the last update, preserve order, and never mutate inputs. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
