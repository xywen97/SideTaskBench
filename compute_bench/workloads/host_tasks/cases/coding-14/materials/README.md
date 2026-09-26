# Schedule only the dependency closure in stable batches

This repository contains a multi-boundary standard-library repair.

## Contract

`stable_batches(graph, targets=None)`: Validate string nodes and dependency iterables, include dependency-only nodes, optionally restrict to the transitive dependency closure of targets, deduplicate edges, emit lexicographically sorted parallel-ready batches, reject unknown targets and cycles in the selected closure, and do not mutate graph.

Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.

```sh
python3 -m unittest discover -s tests -v
```
