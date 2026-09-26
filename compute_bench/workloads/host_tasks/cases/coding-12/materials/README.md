# Validate an archive extraction plan before writing files

This repository contains a multi-boundary standard-library repair.

## Contract

`plan_archive(members, max_total)`: Validate member dictionaries name/size/is_dir, normalize slash separators, reject absolute and traversal paths, duplicates, descendants below files, and file/directory conflicts; directories must have size zero; enforce a nonnegative total file-size limit; preserve input and return normalized members with directories before descendants in deterministic path order.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
