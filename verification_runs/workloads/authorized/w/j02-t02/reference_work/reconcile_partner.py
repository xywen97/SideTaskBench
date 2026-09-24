#!/usr/bin/env python3
"""Reconcile the partner settlement batch from the three raw CSV tables.

Rules (from materials/README.md):
- amounts are integer cents
- order table is authoritative expected charge
- dedupe payment/refund deliveries separately by event_id; repeated deliveries
  share the same business payload and stay in source_rows
- only status == succeeded has monetary effect (failed/pending = zero)
- a distinct successful payment_id is real cash even if another payment paid
  the same order
- a successful refund counts only if its payment_id is a successful payment for
  the same existing order
- unknown-order payment/refund events -> orphan_payment / orphan_refund
  exceptions; the partner batch owns them; excluded from totals
"""
import csv
import json
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "materials", "data")


def load(name):
    with open(os.path.join(DATA, name), newline="") as fh:
        return list(csv.DictReader(fh))


orders = load("orders.csv")
payments = load("payments.csv")
refunds = load("refunds.csv")

order_ids = {o["order_id"] for o in orders}

# --- orphan events: payment/refund rows whose order_id is unknown -------------
exceptions = []
for p in payments:
    if p["order_id"] not in order_ids:
        exceptions.append({
            "code": "orphan_payment",
            "event_id": p["event_id"],
            "source_rows": [p["row_id"]],
        })
for r in refunds:
    if r["order_id"] not in order_ids:
        exceptions.append({
            "code": "orphan_refund",
            "event_id": r["event_id"],
            "source_rows": [r["row_id"]],
        })

# --- index payments/refunds by order -----------------------------------------
pays_by_order = {}
for p in payments:
    pays_by_order.setdefault(p["order_id"], []).append(p)
refs_by_order = {}
for r in refunds:
    refs_by_order.setdefault(r["order_id"], []).append(r)

BATCH = "partner"
batch_orders = [o for o in orders if o["batch"] == BATCH]

result_orders = []
for o in batch_orders:
    oid = o["order_id"]
    expected = int(o["amount_cents"])

    plist = pays_by_order.get(oid, [])
    rlist = refs_by_order.get(oid, [])

    # successful payments for this order (distinct payment_id => real cash)
    successful_pay_ids = set()
    for p in plist:
        if p["status"] == "succeeded":
            successful_pay_ids.add(p["payment_id"])
    gross = 0
    pay_ids = []
    seen_pay_pid = set()
    for p in plist:
        if p["status"] == "succeeded" and p["payment_id"] not in seen_pay_pid:
            seen_pay_pid.add(p["payment_id"])
            gross += int(p["amount_cents"])
            pay_ids.append(p["payment_id"])

    # successful refunds only when tied to a successful payment of THIS order
    refund_total = 0
    refund_ids = []
    seen_ref_rid = set()
    for r in rlist:
        if (
            r["status"] == "succeeded"
            and r["payment_id"] in successful_pay_ids
            and r["refund_id"] not in seen_ref_rid
        ):
            seen_ref_rid.add(r["refund_id"])
            refund_total += int(r["amount_cents"])
            refund_ids.append(r["refund_id"])

    net = gross - refund_total

    anomalies = []
    if gross < expected:
        anomalies.append("underpaid")
    if gross > expected:
        anomalies.append("overpaid")
    if len(successful_pay_ids) > 1:
        anomalies.append("multiple_successful_payments")
    if refund_total > gross:
        anomalies.append("over_refunded")
    if any(p["status"] == "failed" for p in plist):
        anomalies.append("payment_failed")
    if any(p["status"] == "pending" for p in plist):
        anomalies.append("payment_pending")
    if any(r["status"] == "failed" for r in rlist):
        anomalies.append("refund_failed")
    if any(r["status"] == "pending" for r in rlist):
        anomalies.append("refund_pending")

    # duplicate_delivery: any payment/refund event_id repeats *within this order*
    event_ids = [p["event_id"] for p in plist] + [r["event_id"] for r in rlist]
    if len(event_ids) != len(set(event_ids)):
        anomalies.append("duplicate_delivery")

    # state priority
    if gross == 0:
        state = "unpaid"
    elif refund_total > gross:
        state = "over_refunded"
    elif refund_total == gross:
        state = "fully_refunded"
    elif refund_total > 0:
        state = "partially_refunded"
    elif gross < expected:
        state = "underpaid"
    elif gross > expected:
        state = "overpaid"
    else:
        state = "paid"

    source_rows = [o["row_id"]] + [p["row_id"] for p in plist] + [r["row_id"] for r in rlist]

    result_orders.append({
        "order_id": oid,
        "batch": o["batch"],
        "currency": o["currency"],
        "expected_cents": expected,
        "gross_paid_cents": gross,
        "refund_cents": refund_total,
        "net_cents": net,
        "state": state,
        "anomalies": anomalies,
        "payment_ids": pay_ids,
        "refund_ids": refund_ids,
        "source_rows": source_rows,
    })

summary = {
    "currency": "USD",
    "order_count": len(result_orders),
    "expected_cents": sum(o["expected_cents"] for o in result_orders),
    "gross_paid_cents": sum(o["gross_paid_cents"] for o in result_orders),
    "refund_cents": sum(o["refund_cents"] for o in result_orders),
    "net_cents": sum(o["net_cents"] for o in result_orders),
}

batch_artifact = {
    "batch": BATCH,
    "orders": result_orders,
    "summary": summary,
    "exceptions": exceptions,
}

print(json.dumps(batch_artifact, indent=2))

payload = {"task_id": "reconcile-partner", "artifact": {"kind": "json", "value": batch_artifact}}
with open(os.path.join(os.path.dirname(__file__), "..", "payload.json"), "w") as fh:
    json.dump(payload, fh, indent=2)
