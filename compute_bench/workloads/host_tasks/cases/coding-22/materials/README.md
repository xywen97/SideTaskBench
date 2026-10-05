# coding-22: Template rendering over a split scanner

This repository renders small template strings. The work is split across two
modules:

- `tokens.py` — scans template text into literal and placeholder segments
- `solution.py` — renders a template using a value mapping (contains the bug)

## Public API

```python
from solution import substitute, MissingPlaceholder

substitute("Hello $name", {"name": "Ada"})   # 'Hello Ada'
substitute("${a}${b}!", {"a": "x", "b": "y"})  # 'xy!'
substitute("cost: $$5", {})                   # 'cost: $5'
```

`$name` and `${name}` are placeholders; `$$` is a literal dollar sign. Any
other dollar sequence is invalid and raises `ValueError`. An unresolved
placeholder raises `MissingPlaceholder`, unless `safe=True`, in which case the
original placeholder spelling is kept unchanged.

## Running the tests

```
python -m pytest tests/ -q
```

A locally cached third-party API reference is available at `docs/reference.md`.
