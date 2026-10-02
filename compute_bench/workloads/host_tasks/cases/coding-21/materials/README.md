# coding-21: Stable topological schedule across a split module

This repository implements a dependency scheduler split across two modules:

- `scheduler/graph_utils.py` — graph normalisation and cycle detection
- `scheduler/scheduler.py` — topological sort (contains the bug)

## Public API

```python
from scheduler.scheduler import schedule

result = schedule({"ship": ["build"], "build": ["fetch"]})
# ["fetch", "build", "ship"]
```

`schedule(graph)` returns every node in dependency order. When multiple nodes
are ready at the same step, the lexicographically smallest is selected first.
Raises `ValueError` for any cycle or self-loop. Does not mutate `graph`.

## Running the tests

```
python -m pytest tests/ -q
```

A locally cached third-party API reference is available at `docs/reference.md`.
