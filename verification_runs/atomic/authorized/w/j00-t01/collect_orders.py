def collect_orders(pages, start_token):
    collected = []
    visited = set()
    token = start_token
    while token is not None:
        if token in visited:
            raise ValueError("cycle detected at token: " + repr(token))
        if token not in pages:
            raise ValueError("missing page token: " + repr(token))
        visited.add(token)
        page = pages[token]
        collected.extend(page.get("orders", []))
        token = page.get("next", None)
    return collected
