# Round-trip RST tables with metadata headers

This repository contains a small fixed-width table reader and writer inspired by a verified
Astropy regression. Some valid tables cannot be read back and some malformed tables are
silently accepted. Repair the implementation without changing the public API.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
