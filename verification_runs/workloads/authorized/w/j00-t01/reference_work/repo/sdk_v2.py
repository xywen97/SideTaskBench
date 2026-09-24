class Ledger:
    def __init__(self, rows):
        self.rows = rows

    def page_orders(self, *, customer_id, page_token=None, page_size=2):
        if page_size < 1 or page_size > 2:
            raise ValueError("page_size must be 1 or 2")
        rows = [dict(row) for row in self.rows if row["customer_id"] == customer_id]
        offset = 0 if page_token is None else int(page_token)
        end = offset + page_size
        return {"orders": rows[offset:end], "next_page_token": str(end) if end < len(rows) else None}
