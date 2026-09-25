Fix the bug in this Python repository: Produce a stable dependency schedule and reject cycles.

schedule(graph) accepts a mapping from string task names to iterables of prerequisite names. Return every node, including prerequisite-only nodes, after all of its prerequisites. When several nodes are ready, choose the lexicographically smallest. Duplicate dependency entries are one edge. Raise ValueError for any cycle including a self-loop; do not mutate graph.

Inspect the repository, repair solution.py, preserve the documented API and existing correct behavior, and run the public tests. Add useful regression coverage if needed. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
