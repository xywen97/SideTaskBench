def reachable_nodes(graph, targets):
    """Return sorted list of all nodes reachable from targets (inclusive) via prerequisites."""
    targets = list(targets)
    unknown = [t for t in targets if t not in graph]
    if unknown:
        raise ValueError("Unknown targets: " + ", ".join(sorted(unknown)))
    visited = set()
    stack = list(targets)
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for prereq in graph.get(node, []):
            if prereq not in visited:
                stack.append(prereq)
    return sorted(visited)
