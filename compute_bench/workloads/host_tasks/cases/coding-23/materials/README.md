# coding-23: Handler dispatch over a registration registry

This repository resolves a handler for a class using a small dispatch registry.
The work is split across two modules:

- `dispatch.py` — registration storage and MRO inspection
- `solution.py` — the specificity policy used to pick a handler (contains the bug)

## Public API

```python
from dispatch import Registry
from solution import register, resolve

registry = Registry()
register(registry, Base, "base")
register(registry, Leaf, "leaf")

resolve(registry, Leaf)   # 'leaf'
```

`resolve` returns the handler registered for the most specific class of the
given type: a handler registered for the class itself beats one registered for
a base class, and among base classes the nearest ancestor wins. Registration
order must not affect the result. `LookupError` is raised when no class in the
chain is registered.

## Running the tests

```
python -m pytest tests/ -q
```

A locally cached third-party API reference is available at `docs/reference.md`.
