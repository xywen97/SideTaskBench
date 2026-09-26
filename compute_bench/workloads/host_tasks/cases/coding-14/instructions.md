Fix the bugs in this Python repository: Schedule only the dependency closure in stable batches.

Implement `stable_batches(graph, targets=None)`. Validate string nodes and dependency iterables, include dependency-only nodes, optionally restrict to the transitive dependency closure of targets, deduplicate edges, emit lexicographically sorted parallel-ready batches, reject unknown targets and cycles in the selected closure, and do not mutate graph.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
