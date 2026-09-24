def customer_totals(rows, customer_id):
    selected = [r for r in rows if r.get("customer_id") == customer_id and r.get("state") == "settled"]
    return {
        "customer_id": customer_id,
        "order_count": len(selected),
        "net_cents": sum(r["gross_cents"] - r["refund_cents"] for r in selected),
    }
