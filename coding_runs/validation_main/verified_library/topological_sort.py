"""Deterministic topological sorting helper.

This module is intentionally self-contained and uses only the standard
library.  It implements the compatibility helper described in the local
technical reference for this repair.
"""

import heapq


def topological_sort(graph):
    """Return nodes in deterministic topological order.

    ``graph`` maps node names to iterables of prerequisite node names.
    Prerequisite-only names are included in the result.  Ties are broken
    by choosing the lexicographically smallest available node.

    A cycle, including a self-cycle, raises ``ValueError``.  The input
    graph and its containers are not modified.
    """

    # Build an independent set-based representation.  Sets both deduplicate
    # duplicate prerequisite entries and avoid mutating the caller's data.
    prerequisites = {}
    for node, deps in graph.items():
        node_deps = prerequisites.setdefault(node, set())
        for dep in deps:
            node_deps.add(dep)
            prerequisites.setdefault(dep, set())

    dependents = {node: set() for node in prerequisites}
    indegree = {node: len(deps) for node, deps in prerequisites.items()}
    for node, deps in prerequisites.items():
        for dep in deps:
            dependents[dep].add(node)

    available = [node for node, count in indegree.items() if count == 0]
    heapq.heapify(available)

    order = []
    while available:
        node = heapq.heappop(available)
        order.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(available, dependent)

    if len(order) != len(prerequisites):
        raise ValueError("graph contains a cycle")

    return order
