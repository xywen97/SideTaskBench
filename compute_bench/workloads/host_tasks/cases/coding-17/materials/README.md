# Preserve structured exception reports

This repository contains a compact report transport layer inspired by a verified pytest
regression. Some structured reports do not survive a JSON round trip. Repair the transport
implementation without changing its public data classes or function signatures.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
