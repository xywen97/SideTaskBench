def collect_orders(pages, start_token):
    """Collect orders along the page-token chain starting at start_token.

    Follows the in-memory chain of pages, appending each reachable page's
    ``orders`` rows in visit order. Duplicate rows are preserved and empty
    pages are stepped over. A ``next`` value of ``None`` (or a ``None`` start)
    ends the chain. Raises ``ValueError`` on a reachable cycle or a missing
    reachable token. Inputs are never mutated.
    """
    collected = []
    seen = set()
    token = start_token
    while token is not None:
        if token in seen:
            raise ValueError("cycle detected at token: " + repr(token))
        seen.add(token)
        if token not in pages:
            raise ValueError("missing token: " + repr(token))
        page = pages[token]
        rows = page["orders"]
        for row in rows:
            collected.append(row)
        token = page["next"]
    return collected
