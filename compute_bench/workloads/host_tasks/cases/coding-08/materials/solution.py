def schedule(graph):
    result = []
    for node, dependencies in graph.items():
        if not dependencies:
            result.append(node)
    return sorted(result)
