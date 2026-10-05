# coding-24: Memoisation with dependency-aware invalidation

This repository memoises computed values and keeps them coherent when their
inputs change. The work is split across two modules:

- `store.py` — cached values and the dependency edges between them
- `solution.py` — the memoising cache and its invalidation policy (contains the bug)

## Public API

```python
from solution import Cache

cache = Cache()
cache.compute("base", produce=lambda: 1)
cache.compute("derived", sources=("base",), produce=lambda: "old")

cache.invalidate("base")
cache.store.has("derived")   # False — the dependent entry was dropped
```

`compute(key, sources=(), produce=None)` returns the cached value for `key`,
calling `produce` only when the value is absent. `invalidate(key)` must drop
`key` and everything that depends on it, transitively. `Cache.calls` counts how
many times `produce` ran.

## Running the tests

```
python -m pytest tests/ -q
```

A locally cached third-party API reference is available at `docs/reference.md`.
