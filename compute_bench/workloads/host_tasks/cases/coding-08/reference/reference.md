Deterministic dependency scheduling reference

In a prerequisite mapping, each prerequisite must appear before its
dependent. Nodes mentioned only as prerequisites still belong to the
graph. Kahn's algorithm tracks remaining prerequisites and repeatedly
removes ready nodes. A min-heap makes the choice deterministic whenever
multiple names are ready. Duplicate edges should first be deduplicated.

If fewer nodes are emitted than exist in the graph, the remaining
subgraph contains a cycle. A self-dependency is the smallest cycle.
