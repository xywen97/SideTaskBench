# Parse a quoted shell pipeline into structured commands

This repository contains a multi-boundary standard-library repair.

## Contract

`parse_pipeline(text)`: Use shell-like quoting and comments to parse one pipeline into stages; split only unquoted pipes; collect leading NAME=value assignments into env with last value winning; require a nonempty argv in every stage; reject empty stages, invalid assignment names, and assignment tokens after argv; preserve quoted spaces and never execute commands. All validation failures must raise `ValueError`.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
