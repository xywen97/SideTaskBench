# Collect inherited marks in MRO order

This repository contains lightweight metadata helpers inspired by a verified pytest
regression. Metadata lookup and updates become inconsistent when inheritance is involved.
Repair the implementation while preserving the public API and ordinary object behaviour.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
