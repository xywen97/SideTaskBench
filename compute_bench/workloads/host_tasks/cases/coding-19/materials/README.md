# Find modular roots for composite moduli

This repository contains a modular-arithmetic utility inspired by a verified SymPy regression.
The current implementation works for a few small inputs but does not cover the full public
contract. Repair it without changing the public function signature.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
