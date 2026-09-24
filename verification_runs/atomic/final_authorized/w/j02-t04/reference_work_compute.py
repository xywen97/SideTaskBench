import json

packet = {
    "order": {"row_id": "O0000-05", "order_id": "ORD-0000-05", "batch": "marketplace",
              "currency": "USD", "amount_cents": 13049},
    "payments": [
        {"row_id": "P0000-07", "event_id": "PE-0000-05-b", "payment_id": "PAY-0000-05-b",
         "order_id": "ORD-0000-05", "currency": "USD", "amount_cents": 13049, "status": "succeeded"},
        {"row_id": "P0000-06", "event_id": "PE-0000-05-a", "payment_id": "PAY-0000-05-a",
         "order_id": "ORD-0000-05", "currency": "USD", "amount_cents": 13049, "status": "succeeded"},
    ],
    "refunds": [],
}

order = packet["order"]
expected = order["amount_cents"]
payments = packet["payments"]
refunds = packet["refunds"]

# Deduplicate by event_id separately
def dedup(rows):
    seen = {}
    dup = False
    for r in rows:
        eid = r["event_id"]
        if eid in seen:
            dup = True
        else:
            seen[eid] = r
    return list(seen.values()), dup

upays, dup_p = dedup(payments)
urefs, dup_r = dedup(refunds)
duplicate_delivery = dup_p or dup_r

# Counted succeeded payments
counted_pays = {}
for p in upays:
    if p["status"] == "succeeded":
        counted_pays[p["payment_id"]] = p
gross = sum(p["amount_cents"] for p in counted_pays.values())

# Counted succeeded refunds whose payment_id belongs to succeeded payment
counted_refs = {}
succeeded_payment_ids = set(counted_pays.keys())
for r in urefs:
    if r["status"] == "succeeded" and r.get("payment_id") in succeeded_payment_ids:
        counted_refs[r.get("refund_id", r.get("row_id"))] = r
refund_cents = sum(r["amount_cents"] for r in counted_refs.values())

net = gross - refund_cents

# Anomalies
anoms = set()
if gross < expected: anoms.add("underpaid")
if gross > expected: anoms.add("overpaid")
if len(counted_pays) > 1: anoms.add("multiple_successful_payments")
if refund_cents > gross: anoms.add("over_refunded")
if any(p["status"] == "failed" for p in payments): anoms.add("payment_failed")
if any(p["status"] == "pending" for p in payments): anoms.add("payment_pending")
if any(r["status"] == "failed" for r in refunds): anoms.add("refund_failed")
if any(r["status"] == "pending" for r in refunds): anoms.add("refund_pending")
if duplicate_delivery: anoms.add("duplicate_delivery")

# State priority
if gross == 0:
    state = "unpaid"
elif refund_cents > gross:
    state = "over_refunded"
elif refund_cents == gross:
    state = "fully_refunded"
elif refund_cents > 0:
    state = "partially_refunded"
elif gross < expected:
    state = "underpaid"
elif gross > expected:
    state = "overpaid"
else:
    state = "paid"

source_rows = [order["row_id"]] + [p["row_id"] for p in payments] + [r["row_id"] for r in refunds]

result = {
    "order_id": order["order_id"],
    "batch": order["batch"],
    "currency": order["currency"],
    "expected_cents": expected,
    "gross_paid_cents": gross,
    "refund_cents": refund_cents,
    "net_cents": net,
    "state": state,
    "anomalies": sorted(anoms),
    "payment_ids": sorted(counted_pays.keys()),
    "refund_ids": sorted(counted_refs.keys()),
    "source_rows": sorted(source_rows),
}
print(json.dumps(result, indent=2))
with open("payload.json", "w") as f:
    json.dump({"task_id": "reconcile-ord-0000-05", "artifact": {"kind": "json", "value": result}}, f)
