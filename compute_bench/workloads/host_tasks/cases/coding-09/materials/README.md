# Build a deterministic and safe file copy manifest

This repository contains a multi-boundary standard-library repair.

## Contract

`build_copy_plan(root, entries)`: Normalize POSIX and backslash separators, reject absolute paths and traversal, validate nonnegative sizes and 64-digit SHA-256 digests, normalize accepted digests to lowercase, reject normalized duplicates, preserve the input, and return records sorted by normalized path with targets rooted below root. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
