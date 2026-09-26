# Validate an archive extraction plan before writing files

This repository contains a multi-boundary standard-library repair.

## Contract

`plan_archive(members, max_total)`: Each member has exactly the fields name/size/is_dir. Normalize slash separators; reject absolute and traversal paths, duplicates, descendants below files, and file/directory conflicts. Sizes and `max_total` are nonnegative non-boolean integers, `is_dir` is boolean, and directories have size zero. Enforce the total file-size limit, preserve input, and return normalized members with directories before descendants in deterministic path order. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
