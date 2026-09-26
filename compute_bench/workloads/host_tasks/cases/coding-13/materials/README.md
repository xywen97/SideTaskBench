# Compute rolling summaries with missing observations

This repository contains a multi-boundary standard-library repair.

## Contract

`rolling_summary(values, width, min_valid=1)`: For each complete consecutive window return start/count/mean/min/max; None is missing, bool and nonfinite numbers are invalid; width is a positive non-bool integer no larger than the input; min_valid is a positive integer no larger than width; when count is below min_valid return None for all three statistics; do not mutate values.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
