def normalize_order(row):
    return {
        "order_id": row["id"],
        "customer_id": row["customer"],
        "state": "settled" if row["paid"] else "pending",
        "gross_cents": row["amount"],
        "refund_cents": row["refunded"],
    }
