def max_tree_weight(root):
    def visit(node):
        pairs = [visit(child) for child in node.get("children", [])]
        take = node["weight"] + sum(skip for take, skip in pairs)
        skip = sum(max(take, skip) for take, skip in pairs)
        return take, skip
    return max(visit(root))
