Fix the bug in this Python repository: Produce a stable dependency schedule and reject cycles.

scheduler.schedule(graph) accepts a mapping from string task names to iterables of prerequisite names. Return every node, including prerequisite-only nodes, after all of its prerequisites. When several nodes are ready at the same step, choose the lexicographically smallest. Duplicate dependency entries count as one edge. Raise ValueError for any cycle including a self-loop; do not mutate graph.

The repository is split into two modules: graph_utils handles graph normalisation and cycle detection, scheduler/scheduler.py implements the topological sort. The bug is in scheduler/scheduler.py.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
