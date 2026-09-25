def bounded_chain(nodes, start, limit):
    tokens, total, seen = [], 0, set()
    while start is not None:
        if start in seen or start not in nodes: raise ValueError("cycle or missing")
        seen.add(start); item = nodes[start]
        if total + item["value"] > limit: raise ValueError("limit")
        total += item["value"]; tokens.append(start); start = item["next"]
    return {"tokens": tokens, "total": total}
