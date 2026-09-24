#!/usr/bin/env python3
"""Validate a batch artifact against materials/README.md invariants."""
import json
import sys

sys.path.insert(0, ".")
from reconcile import main  # noqa


def validate(batch):
    art = main(batch)
    assert art["kind"] == "json"
    v = art["value"]
    orders = v["orders"]
    errs = []

    # order_count and uniqueness
    ids = [o["order_id"] for o in orders]
    if len(ids) != len(set(ids)):
        errs.append("duplicate order_id in orders")
    if v["summary"]["order_count"] != len(orders):
        errs.append("order_count mismatch")

    # totals
    for key in ("expected_cents", "gross_paid_cents", "refund_cents", "net_cents"):
        tot = sum(o[key] for o in orders)
        if v["summary"][key] != tot:
            errs.append(f"summary {key}: {v['summary'][key]} != {tot}")
    if v["summary"]["currency"] != "USD":
        errs.append("currency not USD")

    for o in orders:
        # net = gross - refund
        if o["net_cents"] != o["gross_paid_cents"] - o["refund_cents"]:
            errs.append(f"{o['order_id']}: net mismatch")
        # no repeated rows / ids / anomaly codes
        if len(o["source_rows"]) != len(set(o["source_rows"])):
            errs.append(f"{o['order_id']}: repeated source_rows")
        if len(o["payment_ids"]) != len(set(o["payment_ids"])):
            errs.append(f"{o['order_id']}: repeated payment_ids")
        if len(o["refund_ids"]) != len(set(o["refund_ids"])):
            errs.append(f"{o['order_id']}: repeated refund_ids")
        if len(o["anomalies"]) != len(set(o["anomalies"])):
            errs.append(f"{o['order_id']}: repeated anomaly codes")
        # order row present
        if not any(r.startswith("O") for r in o["source_rows"]):
            errs.append(f"{o['order_id']}: missing order source row")

    # exceptions uniqueness
    for e in v["exceptions"]:
        if len(e["source_rows"]) != len(set(e["source_rows"])):
            errs.append(f"exception {e.get('event_id')}: repeated source_rows")

    return art, errs


if __name__ == "__main__":
    for batch in sys.argv[1:] or ["marketplace"]:
        art, errs = validate(batch)
        print(f"batch={batch} status={'OK' if not errs else 'FAIL'}")
        for e in errs:
            print("  -", e)
