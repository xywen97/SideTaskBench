import json

order = {
  "row_id": "O0000-05",
  "order_id": "ORD-0000-05",
  "batch": "marketplace",
  "currency": "USD",
  "amount_cents": 13049
}
payments = [
  {"row_id":"P0000-07","event_id":"PE-0000-05-b","payment_id":"PAY-0000-05-b","order_id":"ORD-0000-05","currency":"USD","amount_cents":13049,"status":"succeeded"},
  {"row_id":"P0000-06","event_id":"PE-0000-05-a","payment_id":"PAY-0000-05-a","order_id":"ORD-0000-05","currency":"USD","amount_cents":13049,"status":"succeeded"},
]
refunds = []

expected = order["amount_cents"]

def dedup(rows):
    seen=set(); out=[]
    for r in rows:
        eid=r["event_id"]
        if eid in seen: continue
        seen.add(eid); out.append(r)
    return out

dp = dedup(payments)
dr = dedup(refunds)

def has_dup(rows):
    seen=set()
    for r in rows:
        if r["event_id"] in seen: return True
        seen.add(r["event_id"])
    return False
dup = has_dup(payments) or has_dup(refunds)

succeeded_pays = {r["payment_id"] for r in dp if r["status"]=="succeeded"}
gross = sum(r["amount_cents"] for r in dp if r["status"]=="succeeded")
payment_ids = sorted(succeeded_pays)

counted_refunds=[r for r in dr if r["status"]=="succeeded" and r["payment_id"] in succeeded_pays]
refund = sum(r["amount_cents"] for r in counted_refunds)
refund_ids = sorted({r["refund_id"] for r in counted_refunds}) if counted_refunds else []

net = gross - refund

anomalies=set()
if gross < expected: anomalies.add("underpaid")
if gross > expected: anomalies.add("overpaid")
if len(payment_ids) > 1: anomalies.add("multiple_successful_payments")
if refund > gross: anomalies.add("over_refunded")
if any(r["status"]=="failed" for r in payments): anomalies.add("payment_failed")
if any(r["status"]=="pending" for r in payments): anomalies.add("payment_pending")
if any(r["status"]=="failed" for r in refunds): anomalies.add("refund_failed")
if any(r["status"]=="pending" for r in refunds): anomalies.add("refund_pending")
if dup: anomalies.add("duplicate_delivery")

if gross == 0:
    state="unpaid"
elif refund > gross:
    state="over_refunded"
elif refund == gross:
    state="fully_refunded"
elif refund > 0:
    state="partially_refunded"
elif gross < expected:
    state="underpaid"
elif gross > expected:
    state="overpaid"
else:
    state="paid"

source_rows = sorted([order["row_id"]] + [r["row_id"] for r in payments] + [r["row_id"] for r in refunds])

result = {
  "order_id": order["order_id"],
  "batch": order["batch"],
  "currency": order["currency"],
  "expected_cents": expected,
  "gross_paid_cents": gross,
  "refund_cents": refund,
  "net_cents": net,
  "state": state,
  "anomalies": sorted(anomalies),
  "payment_ids": payment_ids,
  "refund_ids": refund_ids,
  "source_rows": source_rows,
}
print(json.dumps(result, indent=2))
with open("reference_work/result.json","w") as f:
    json.dump(result, f, indent=2)
