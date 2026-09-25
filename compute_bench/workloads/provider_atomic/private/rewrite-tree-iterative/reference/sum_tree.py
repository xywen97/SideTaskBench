def sum_tree(node):
    total = 0
    pending = [node]
    while pending:
        current = pending.pop()
        total += current["value"]
        pending.extend(current.get("children", []))
    return total
