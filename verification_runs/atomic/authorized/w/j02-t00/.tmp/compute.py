import json

order = {"row_id":"O0000-01","order_id":"ORD-0000-01","batch":"web","currency":"USD","amount_cents":10699}
payments = [{"row_id":"P0000-01","event_id":"PE-0000-01-a","payment_id":"PAY-0000-01-a","order_id":"ORD-0000-01","currency":"USD","amount_cents":10699,"status":"succeeded"}]
refunds = [{"row_id":"R0000-05","event_id":"RE-0000-01","refund_id":"REF-0000-01","payment_id":"PAY-0000-01-a","order_id":"ORD-0000-01","currency":"USD","amount_cents":100,"status":"failed"}]

expected = order["amount_cents"]

# dedup payments/refunds by event_id
def dedup(rows):
    seen={}
    dup=False
    for r in rows:
        eid=r["event_id"]
        if eid in seen:
            dup=True
        else:
            seen[eid]=r
    return list(seen.values()), dup

p_dedup, p_dup = dedup(payments)
r_dedup, r_dup = dedup(refunds)
duplicate_delivery = p_dup or r_dup

# succeeded payments
succ_pay_ids = sorted({p["payment_id"] for p in p_dedup if p["status"]=="succeeded"})
gross = sum(p["amount_cents"] for p in p_dedup if p["status"]=="succeeded")

# counted refunds: succeeded and payment_id in succ_pay_ids
counted_refunds = [r for r in r_dedup if r["status"]=="succeeded" and r["payment_id"] in succ_pay_ids]
refund_ids = sorted({r["refund_id"] for r in counted_refunds})
refund_cents = sum(r["amount_cents"] for r in counted_refunds)

net = gross - refund_cents

# source rows
source_rows = sorted([order["row_id"]] + [p["row_id"] for p in payments] + [r["row_id"] for r in refunds])

# anomalies
anomalies=set()
if gross < expected: anomalies.add("underpaid")
if gross > expected: anomalies.add("overpaid")
if len(succ_pay_ids) > 1: anomalies.add("multiple_successful_payments")
if refund_cents > gross: anomalies.add("over_refunded")
if any(p["status"]=="failed" for p in payments): anomalies.add("payment_failed")
if any(p["status"]=="pending" for p in payments): anomalies.add("payment_pending")
if any(r["status"]=="failed" for r in refunds): anomalies.add("refund_failed")
if any(r["status"]=="pending" for r in refunds): anomalies.add("refund_pending")
if duplicate_delivery: anomalies.add("duplicate_delivery")

# state
if gross == 0:
    state="unpaid"
elif refund_cents > gross:
    state="over_refunded"
elif refund_cents == gross:
    state="fully_refunded"
elif refund_cents > 0:
    state="partially_refunded"
elif gross < expected:
    state="underpaid"
elif gross > expected:
    state="overpaid"
else:
    state="paid"

result = {
    "order_id": order["order_id"],
    "batch": order["batch"],
    "currency": order["currency"],
    "expected_cents": expected,
    "gross_paid_cents": gross,
    "refund_cents": refund_cents,
    "net_cents": net,
    "state": state,
    "anomalies": sorted(anomalies),
    "payment_ids": succ_pay_ids,
    "refund_ids": refund_ids,
    "source_rows": source_rows,
}
print(json.dumps(result, indent=2))

envelope = {"task_id":"reconcile-ord-0000-01","artifact":{"kind":"json","value":result}}
with open("/workspace/payload.json","w") as f:
    json.dump(envelope,f)
