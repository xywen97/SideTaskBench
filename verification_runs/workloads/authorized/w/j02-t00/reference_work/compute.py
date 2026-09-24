import csv, json, collections

M = "/workspace/materials/data/"
def load(name):
    with open(M+name, newline='') as f:
        return list(csv.DictReader(f))

orders = load("orders.csv")
payments = load("payments.csv")
refunds = load("refunds.csv")

orders_by_id = {o["order_id"]: o for o in orders}

# ---- Payments: dedup by event_id ----
pay_by_event = {}
for p in payments:
    pay_by_event.setdefault(p["event_id"], []).append(p)

# representative per event (first row); same business payload
pay_reps = {e: rows[0] for e, rows in pay_by_event.items()}

# successful payments per order (distinct payment_id), and orphan detection
successful_pay_by_order = collections.defaultdict(dict)  # order_id -> {payment_id: rep}
for e, rep in pay_reps.items():
    if rep["order_id"] not in orders_by_id:
        continue  # orphan -> partner
    if rep["status"] == "succeeded":
        successful_pay_by_order[rep["order_id"]][rep["payment_id"]] = rep

# successful payment_ids globally (for refund validation)
success_payment_ids = set()
for oid, d in successful_pay_by_order.items():
    success_payment_ids.update(d.keys())

# ---- Refunds: dedup by event_id ----
ref_by_event = {}
for r in refunds:
    ref_by_event.setdefault(r["event_id"], []).append(r)
ref_reps = {e: rows[0] for e, rows in ref_by_event.items()}

paid_refunds_by_order = collections.defaultdict(list)  # order_id -> [rep]
for e, rep in ref_reps.items():
    if rep["order_id"] not in orders_by_id:
        continue  # orphan -> partner
    if rep["status"] == "succeeded" and rep["payment_id"] in success_payment_ids:
        paid_refunds_by_order[rep["order_id"]].append(rep)

# ---- related physical rows per order ----
pay_rows_by_order = collections.defaultdict(list)
for p in payments:
    pay_rows_by_order[p["order_id"]].append(p)
ref_rows_by_order = collections.defaultdict(list)
for r in refunds:
    ref_rows_by_order[r["order_id"]].append(r)

def compute_order(o):
    oid = o["order_id"]
    expected = int(o["amount_cents"])
    payrows = pay_rows_by_order[oid]
    refrows = ref_rows_by_order[oid]

    # distinct successful payments (monetary)
    succ = successful_pay_by_order.get(oid, {})
    gross = sum(int(rep["amount_cents"]) for rep in succ.values())
    payment_ids = sorted(succ.keys())

    payrefs = paid_refunds_by_order.get(oid, [])
    refund_cents = sum(int(rep["amount_cents"]) for rep in payrefs)
    refund_ids = sorted({rep["refund_id"] for rep in payrefs})

    net = gross - refund_cents

    # anomalies
    an = []
    if gross < expected: an.append("underpaid")
    if gross > expected: an.append("overpaid")
    if len(succ) > 1: an.append("multiple_successful_payments")
    if refund_cents > gross: an.append("over_refunded")
    statuses_p = {r["status"] for r in payrows}
    statuses_r = {r["status"] for r in refrows}
    if "failed" in statuses_p: an.append("payment_failed")
    if "pending" in statuses_p: an.append("payment_pending")
    if "failed" in statuses_r: an.append("refund_failed")
    if "pending" in statuses_r: an.append("refund_pending")
    # duplicate_delivery: any event_id repeats (within payments or refunds)
    pay_ev = [r["event_id"] for r in payrows]
    ref_ev = [r["event_id"] for r in refrows]
    if len(pay_ev) != len(set(pay_ev)) or len(ref_ev) != len(set(ref_ev)):
        an.append("duplicate_delivery")

    # state
    if gross == 0: state = "unpaid"
    elif refund_cents > gross: state = "over_refunded"
    elif refund_cents == gross: state = "fully_refunded"
    elif refund_cents > 0: state = "partially_refunded"
    elif gross < expected: state = "underpaid"
    elif gross > expected: state = "overpaid"
    else: state = "paid"

    source_rows = [o["row_id"]] + [r["row_id"] for r in payrows] + [r["row_id"] for r in refrows]
    return {
        "order_id": oid,
        "batch": o["batch"],
        "currency": o["currency"],
        "expected_cents": expected,
        "gross_paid_cents": gross,
        "refund_cents": refund_cents,
        "net_cents": net,
        "state": state,
        "anomalies": an,
        "payment_ids": payment_ids,
        "refund_ids": refund_ids,
        "source_rows": source_rows,
    }

web_orders = sorted([o for o in orders if o["batch"] == "web"], key=lambda o: o["order_id"])
computed = [compute_order(o) for o in web_orders]

summary = {
    "currency": "USD",
    "order_count": len(computed),
    "expected_cents": sum(c["expected_cents"] for c in computed),
    "gross_paid_cents": sum(c["gross_paid_cents"] for c in computed),
    "refund_cents": sum(c["refund_cents"] for c in computed),
    "net_cents": sum(c["net_cents"] for c in computed),
}

batch = {"batch": "web", "orders": computed, "summary": summary, "exceptions": []}
print(json.dumps(batch, indent=2))
with open("web_batch.json", "w") as f:
    json.dump(batch, f, indent=2)
