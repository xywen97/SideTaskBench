def fetch_all(fetch_page, start_cursor):
    items = []
    cursor = start_cursor
    seen = set()
    while cursor is not None:
        if cursor in seen:
            raise ValueError("repeated cursor")
        seen.add(cursor)
        page = fetch_page(cursor)
        items.extend(page["items"])
        cursor = page["next_cursor"]
    return items
