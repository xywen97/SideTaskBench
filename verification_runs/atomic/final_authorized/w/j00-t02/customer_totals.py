def customer_totals(rows, customer_id):
    selected = [
        r
        for r in rows
        if r["customer_id"] == customer_id and r["state"] == "settled"
    ]
    net_cents = 0
    for r in selected:
        net_cents += r["gross_cents"] - r["refund_cents"]
    return {
        "customer_id": customer_id,
        "order_count": len(selected),
        "net_cents": net_cents,
    }
