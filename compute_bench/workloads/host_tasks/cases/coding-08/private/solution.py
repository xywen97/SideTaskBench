import heapq

def schedule(graph):
    dependencies = {node: set(values) for node, values in graph.items()}
    for values in list(dependencies.values()):
        for node in values:
            dependencies.setdefault(node, set())
    followers = {node: set() for node in dependencies}
    for node, values in dependencies.items():
        for prerequisite in values:
            followers[prerequisite].add(node)
    ready = [node for node, values in dependencies.items() if not values]
    heapq.heapify(ready)
    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for follower in followers[node]:
            dependencies[follower].remove(node)
            if not dependencies[follower]:
                heapq.heappush(ready, follower)
    if len(result) != len(dependencies):
        raise ValueError("dependency cycle")
    return result
