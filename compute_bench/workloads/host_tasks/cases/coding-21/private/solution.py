"""Topological scheduler: produces a stable dependency order."""

import heapq

from graph_utils import normalize_graph, detect_cycle


def schedule(graph):
    """Return a topological ordering of all nodes in *graph*.

    *graph* maps task names (strings) to iterables of prerequisite names.
    Every node, including prerequisite-only nodes, appears in the result.
    When several nodes are ready at the same step, the lexicographically
    smallest is chosen first.  Raises ValueError for any cycle or self-loop.
    Does not mutate *graph*.
    """
    deps = normalize_graph(graph)
    detect_cycle(deps)

    followers = {node: [] for node in deps}
    in_degree = {node: len(values) for node, values in deps.items()}
    for node, values in deps.items():
        for prereq in values:
            followers[prereq].append(node)

    ready = [node for node, degree in in_degree.items() if degree == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for follower in followers[node]:
            in_degree[follower] -= 1
            if in_degree[follower] == 0:
                heapq.heappush(ready, follower)
    return result
