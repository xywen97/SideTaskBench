"""Graph normalisation and cycle detection utilities."""


def normalize_graph(graph):
    """Return a dict mapping every node to a set of its prerequisite nodes.

    Prerequisite-only nodes (those that appear as dependencies but have no
    entry of their own in *graph*) are added with an empty dependency set.
    Duplicate entries in a dependency iterable count as one edge.
    The original *graph* mapping is not mutated.
    """
    deps = {node: set(values) for node, values in graph.items()}
    for values in list(deps.values()):
        for node in values:
            deps.setdefault(node, set())
    return deps


def detect_cycle(deps):
    """Raise ValueError if *deps* (a dict of node -> set of prerequisites) contains a cycle.

    Uses iterative DFS with three-colour marking (white/grey/black).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {node: WHITE for node in deps}
    for start in deps:
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(deps[start]))]
        colour[start] = GREY
        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
                if colour[child] == GREY:
                    raise ValueError("dependency cycle")
                if colour[child] == WHITE:
                    colour[child] = GREY
                    stack.append((child, iter(deps[child])))
            except StopIteration:
                colour[node] = BLACK
                stack.pop()
