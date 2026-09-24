#!/usr/bin/env python3
"""Reconcile a settlement batch per materials/README.md.

Usage: reconcile.py BATCH
Prints the batch artifact JSON to stdout.
"""
import csv
import json
import os
import sys
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), "..", "materials", "data")


def load(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def main(batch):
    orders = load("orders.csv")
    payments = load("payments.csv")
    refunds = load("refunds.csv")

    known_orders = {o["order_id"] for o in orders}

    # --- Deduplicate deliveries by event_id, keep all physical rows. ---
    # payments[order_id] -> list of distinct events (by event_id), each with
    #   its physical row_ids.
    pay_by_order = defaultdict(list)   # order_id -> [event dicts]
    pay_events = {}                    # event_id -> event dict
    pay_dup = defaultdict(set)         # order_id -> event_ids that repeat
    orphan_payments = []               # events for unknown orders

    for r in payments:
        eid = r["event_id"]
        if eid in pay_events:
            ev = pay_events[eid]
            ev["row_ids"].append(r["row_id"])
            # repeated delivery for this event
            pay_dup.setdefault(r["order_id"], set()).add(eid)
            continue
        ev = {
            "event_id": eid,
            "payment_id": r["payment_id"],
            "order_id": r["order_id"],
            "amount_cents": int(r["amount_cents"]),
            "status": r["status"],
            "row_ids": [r["row_id"]],
        }
        pay_events[eid] = ev
        if r["order_id"] in known_orders:
            pay_by_order[r["order_id"]].append(ev)
        else:
            orphan_payments.append(ev)

    ref_by_order = defaultdict(list)
    ref_events = {}
    ref_dup = defaultdict(set)
    orphan_refunds = []

    for r in refunds:
        eid = r["event_id"]
        if eid in ref_events:
            ev = ref_events[eid]
            ev["row_ids"].append(r["row_id"])
            ref_dup.setdefault(r["order_id"], set()).add(eid)
            continue
        ev = {
            "event_id": eid,
            "refund_id": r["refund_id"],
            "payment_id": r["payment_id"],
            "order_id": r["order_id"],
            "amount_cents": int(r["amount_cents"]),
            "status": r["status"],
            "row_ids": [r["row_id"]],
        }
        ref_events[eid] = ev
        if r["order_id"] in known_orders:
            ref_by_order[r["order_id"]].append(ev)
        else:
            orphan_refunds.append(ev)

    # Map of successful payment_id -> order_id (for refund validity).
    successful_pay_ids = defaultdict(set)  # payment_id -> {order_id}
    for pid, ev in pay_events.items():
        pass
    for ev in pay_events.values():
        if ev["status"] == "succeeded":
            successful_pay_ids[ev["payment_id"]].add(ev["order_id"])

    batch_orders = [o for o in orders if o["batch"] == batch]

    out_orders = []
    for o in batch_orders:
        oid = o["order_id"]
        exp = int(o["amount_cents"])
        pevs = pay_by_order.get(oid, [])
        revs = ref_by_order.get(oid, [])

        gross = sum(e["amount_cents"] for e in pevs if e["status"] == "succeeded")

        # refund counts only if its payment_id is a successful payment for the
        # same existing order
        refund = 0
        refund_ids = []
        for e in revs:
            if e["status"] != "succeeded":
                continue
            if oid in successful_pay_ids.get(e["payment_id"], set()):
                refund += e["amount_cents"]
                refund_ids.append(e["refund_id"])
        refund_ids = sorted(set(refund_ids))

        payment_ids = sorted({e["payment_id"] for e in pevs if e["status"] == "succeeded"})
        net = gross - refund

        anomalies = []
        if gross < exp:
            anomalies.append("underpaid")
        if gross > exp:
            anomalies.append("overpaid")
        if len(payment_ids) > 1:
            anomalies.append("multiple_successful_payments")
        if refund > gross:
            anomalies.append("over_refunded")
        if any(e["status"] == "failed" for e in pevs):
            anomalies.append("payment_failed")
        if any(e["status"] == "pending" for e in pevs):
            anomalies.append("payment_pending")
        if any(e["status"] == "failed" for e in revs):
            anomalies.append("refund_failed")
        if any(e["status"] == "pending" for e in revs):
            anomalies.append("refund_pending")
        dup = bool(pay_dup.get(oid)) or bool(ref_dup.get(oid))
        if dup:
            anomalies.append("duplicate_delivery")

        # state priority
        if gross == 0:
            state = "unpaid"
        elif refund > gross:
            state = "over_refunded"
        elif refund == gross:
            state = "fully_refunded"
        elif refund > 0:
            state = "partially_refunded"
        elif gross < exp:
            state = "underpaid"
        elif gross > exp:
            state = "overpaid"
        else:
            state = "paid"

        source_rows = [o["row_id"]]
        for e in pevs:
            source_rows.extend(e["row_ids"])
        for e in revs:
            source_rows.extend(e["row_ids"])

        out_orders.append({
            "order_id": oid,
            "batch": batch,
            "currency": o["currency"],
            "expected_cents": exp,
            "gross_paid_cents": gross,
            "refund_cents": refund,
            "net_cents": net,
            "state": state,
            "anomalies": anomalies,
            "payment_ids": payment_ids,
            "refund_ids": refund_ids,
            "source_rows": source_rows,
        })

    summary = {
        "currency": "USD",
        "order_count": len(out_orders),
        "expected_cents": sum(x["expected_cents"] for x in out_orders),
        "gross_paid_cents": sum(x["gross_paid_cents"] for x in out_orders),
        "refund_cents": sum(x["refund_cents"] for x in out_orders),
        "net_cents": sum(x["net_cents"] for x in out_orders),
    }

    # Orphan-event exceptions are owned by the partner batch only.
    exceptions = []
    if batch == "partner":
        for ev in orphan_payments:
            exceptions.append({
                "code": "orphan_payment",
                "event_id": ev["event_id"],
                "source_rows": list(ev["row_ids"]),
            })
        for ev in orphan_refunds:
            exceptions.append({
                "code": "orphan_refund",
                "event_id": ev["event_id"],
                "source_rows": list(ev["row_ids"]),
            })

    return {
        "kind": "json",
        "value": {
            "batch": batch,
            "orders": out_orders,
            "summary": summary,
            "exceptions": exceptions,
        },
    }


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=2))
