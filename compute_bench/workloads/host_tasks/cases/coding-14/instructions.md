Fix the bugs in this Python repository: Schedule only the dependency closure in stable batches.

Implement `stable_batches(graph, targets=None)`. Validate nonempty string nodes and dependency iterables, include dependency-only nodes, and optionally restrict scheduling to the transitive dependency closure of targets. Deduplicate edges, emit lexicographically sorted parallel-ready batches, reject unknown targets and cycles in the selected closure, and do not mutate graph. All validation failures must raise `ValueError`.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
