from sdk_v2 import Ledger


def monthly_statement(rows, customer_id):
    ledger = Ledger(rows)
    order_count = 0
    net_cents = 0
    page_token = None
    while True:
        page = ledger.page_orders(customer_id=customer_id, page_token=page_token)
        for order in page["orders"]:
            if order["state"] == "settled":
                order_count += 1
                net_cents += order["gross_cents"] - order["refund_cents"]
        page_token = page["next_page_token"]
        if page_token is None:
            break
    return {"customer_id": customer_id, "order_count": order_count,
            "net_cents": net_cents}
