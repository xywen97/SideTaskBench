# Compute rolling summaries with missing observations

This repository contains a multi-boundary standard-library repair.

## Contract

`rolling_summary(values, width, min_valid=1)`: Materialize any finite iterable, including a one-shot generator, without mutating its source. For each complete consecutive window return start/count/mean/min/max. Values may be built-in int/float or None; None is missing, while bool, strings, and nonfinite numbers are invalid. Width is a positive non-boolean integer no larger than the materialized input; min_valid is a positive non-boolean integer no larger than width. When count is below min_valid, return None for all three statistics. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
