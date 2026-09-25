def collect_pages(pages, start):
    out, seen = [], set()
    while start is not None:
        if start in seen or start not in pages:
            raise ValueError("cycle or missing token")
        seen.add(start)
        page = pages[start]
        out.extend(page["items"])
        start = page["next"]
    return out
