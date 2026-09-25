# Produce a stable dependency schedule and reject cycles

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

schedule(graph) accepts a mapping from string task names to iterables of prerequisite names. Return every node, including prerequisite-only nodes, after all of its prerequisites. When several nodes are ready, choose the lexicographically smallest. Duplicate dependency entries are one edge. Raise ValueError for any cycle including a self-loop; do not mutate graph.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

External reference documents may be found with the reference search tool.
The repository and this issue contain all requirements needed for the repair.
