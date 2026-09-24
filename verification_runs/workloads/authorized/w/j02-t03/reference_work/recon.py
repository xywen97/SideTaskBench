import csv, json, os

BASE = "/workspace/materials/data"

def load(name):
    with open(os.path.join(BASE, name), newline="") as f:
        return list(csv.DictReader(f))

orders = load("orders.csv")
payments = load("payments.csv")
refunds = load("refunds.csv")

order_ids = {o["order_id"] for o in orders}

# group physical rows per order
pay_by_order = {}
for p in payments:
    pay_by_order.setdefault(p["order_id"], []).append(p)
ref_by_order = {}
for r in refunds:
    ref_by_order.setdefault(r["order_id"], []).append(r)

findings = []
for o in orders:
    oid = o["order_id"]
    expected = int(o["amount_cents"])
    prows = pay_by_order.get(oid, [])
    rrows = ref_by_order.get(oid, [])

    codes = set()

    # distinct successful payments
    succ_pays = [p for p in prows if p["status"] == "succeeded"]
    # dedupe by event_id for monetary effect
    seen_ev = set()
    distinct_succ_pay_ids = []
    gross = 0
    for p in succ_pays:
        key = p["event_id"]
        if key in seen_ev:
            continue
        seen_ev.add(key)
        if p["payment_id"] not in distinct_succ_pay_ids:
            distinct_succ_pay_ids.append(p["payment_id"])
        gross += int(p["amount_cents"])
    if len(distinct_succ_pay_ids) > 1:
        codes.add("multiple_successful_payments")
    if any(p["status"] == "failed" for p in prows):
        codes.add("payment_failed")
    if any(p["status"] == "pending" for p in prows):
        codes.add("payment_pending")

    # refunds: successful refund counted only if payment_id is a successful payment
    # for the same existing order
    succ_pay_ids_for_order = set(distinct_succ_pay_ids)
    refund_total = 0
    seen_rev = set()
    for r in rrows:
        if r["status"] != "succeeded":
            continue
        if r["event_id"] in seen_rev:
            continue
        if r["payment_id"] in succ_pay_ids_for_order:
            seen_rev.add(r["event_id"])
            refund_total += int(r["amount_cents"])
    if any(r["status"] == "failed" for r in rrows):
        codes.add("refund_failed")
    if any(r["status"] == "pending" for r in rrows):
        codes.add("refund_pending")

    # duplicate delivery: any payment/refund event_id repeats (within all related rows)
    ev_counts = {}
    for row in prows + rrows:
        ev_counts[row["event_id"]] = ev_counts.get(row["event_id"], 0) + 1
    if any(c > 1 for c in ev_counts.values()):
        codes.add("duplicate_delivery")

    if gross < expected:
        codes.add("underpaid")
    if gross > expected:
        codes.add("overpaid")
    if refund_total > gross:
        codes.add("over_refunded")

    if codes:
        source_rows = [o["row_id"]] + [p["row_id"] for p in prows] + [r["row_id"] for r in rrows]
        findings.append({
            "subject_id": oid,
            "codes": sorted(codes),
            "source_rows": source_rows,
        })

# orphans
for p in payments:
    if p["order_id"] not in order_ids:
        findings.append({
            "subject_id": p["event_id"],
            "codes": ["orphan_payment"],
            "source_rows": [p["row_id"]],
        })
for r in refunds:
    if r["order_id"] not in order_ids:
        findings.append({
            "subject_id": r["event_id"],
            "codes": ["orphan_refund"],
            "source_rows": [r["row_id"]],
        })

result = {"findings": findings}
print(json.dumps(result, indent=2))

out = "/workspace/reference_work/findings.json"
with open(out, "w") as f:
    json.dump(result, f, indent=2)
print("\nwrote", out)
