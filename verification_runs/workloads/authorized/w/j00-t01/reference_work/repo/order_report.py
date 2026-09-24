from sdk_v2 import Ledger


def monthly_statement(rows, customer_id):
    ledger = Ledger(rows)
    orders = []
    token = None
    while True:
        page = ledger.page_orders(customer_id=customer_id, page_token=token)
        orders.extend(page["orders"])
        token = page["next_page_token"]
        if token is None:
            break
    settled = [o for o in orders if o["state"] == "settled"]
    return {"customer_id": customer_id, "order_count": len(settled),
            "net_cents": sum(o["gross_cents"] - o["refund_cents"] for o in settled)}
