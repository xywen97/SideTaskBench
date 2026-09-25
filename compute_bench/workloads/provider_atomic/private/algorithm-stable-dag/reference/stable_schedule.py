import heapq
def stable_schedule(graph):
    deps = {k: set(v) for k, v in graph.items()}
    for values in list(deps.values()):
        for item in values: deps.setdefault(item, set())
    followers = {k: set() for k in deps}
    for node, values in deps.items():
        for value in values: followers[value].add(node)
    ready = [k for k, v in deps.items() if not v]; heapq.heapify(ready); out = []
    while ready:
        node = heapq.heappop(ready); out.append(node)
        for nxt in followers[node]:
            deps[nxt].remove(node)
            if not deps[nxt]: heapq.heappush(ready, nxt)
    if len(out) != len(deps): raise ValueError("cycle")
    return out
