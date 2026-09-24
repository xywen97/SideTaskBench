"""One order (or one orphan event) per packet; platform totals the returned rows."""

from copy import deepcopy

from ..contracts import WorkloadCase
from .atomic_common import artifact, equal, select, value_of


def reconcile(packet):
    data = packet["input"]
    if packet["operation"] == "classify_orphan_event":
        event = data["event"]
        if event["order_id"] in data["known_order_ids"]:
            raise ValueError("This packet must contain one actual orphan event")
        return {"code": "orphan_" + data["event_type"], "event_id": event["event_id"], "source_rows": [event["row_id"]]}
    order, payments, refunds = data["order"], data["payments"], data["refunds"]
    if any(r["order_id"] != order["order_id"] for r in payments + refunds):
        raise ValueError("A reconciliation packet owns exactly one order")
    p = {r["event_id"]: r for r in payments}
    r = {r["event_id"]: r for r in refunds}
    successes = {v["payment_id"]: v for v in p.values() if v["status"] == "succeeded"}
    returned = {v["refund_id"]: v for v in r.values() if v["status"] == "succeeded" and v["payment_id"] in successes}
    gross = sum(v["amount_cents"] for v in successes.values())
    refunded = sum(v["amount_cents"] for v in returned.values())
    conditions = {"underpaid": gross < order["amount_cents"], "overpaid": gross > order["amount_cents"],
                  "multiple_successful_payments": len(successes) > 1, "over_refunded": refunded > gross,
                  "duplicate_delivery": len(p) != len(payments) or len(r) != len(refunds)}
    conditions.update({kind + "_" + state: any(v["status"] == state for v in rows)
                       for kind, rows in (("payment", payments), ("refund", refunds)) for state in ("failed", "pending")})
    state = ("unpaid" if gross == 0 else "over_refunded" if refunded > gross else
             "fully_refunded" if refunded == gross else "partially_refunded" if refunded else
             "underpaid" if gross < order["amount_cents"] else "overpaid" if gross > order["amount_cents"] else "paid")
    return {"order_id": order["order_id"], "batch": order["batch"], "currency": order["currency"],
            "expected_cents": order["amount_cents"], "gross_paid_cents": gross, "refund_cents": refunded,
            "net_cents": gross - refunded, "state": state, "anomalies": sorted(k for k, v in conditions.items() if v),
            "payment_ids": sorted(successes), "refund_ids": sorted(returned),
            "source_rows": sorted([order["row_id"], *[v["row_id"] for v in payments + refunds]])}


def ledger(parts, tasks):
    rows = [deepcopy(parts[t["task_id"]]) for t in tasks if t["task_id"] in parts and t["packet"]["operation"] == "reconcile_one_order"]
    exceptions = [deepcopy(parts[t["task_id"]]) for t in tasks if t["task_id"] in parts and t["packet"]["operation"] == "classify_orphan_event"]
    rows.sort(key=lambda row: row["order_id"])
    exceptions.sort(key=lambda row: row["event_id"])
    fields = ("expected_cents", "gross_paid_cents", "refund_cents", "net_cents")
    return {"orders": rows, "exceptions": exceptions,
            "summary": {"currency": "USD", "order_count": len(rows), **{f: sum(r[f] for r in rows) for f in fields}}}


def build_case(definition, materials, seed=0):
    tasks = deepcopy(definition["tasks"])
    if any(t["packet"]["operation"] not in {"reconcile_one_order", "classify_orphan_event"} for t in tasks):
        raise ValueError("Unknown reconciliation packet")
    expected = {t["task_id"]: reconcile(t["packet"]) for t in tasks}
    order_ids = [v["order_id"] for v in expected.values() if "order_id" in v]
    if len(order_ids) != len(set(order_ids)):
        raise ValueError("Atomic packets must have distinct order ownership")
    final = ledger(expected, tasks)

    def grade_task(task_id, result):
        return {"passed": task_id in expected and equal(value_of(result), expected[task_id])}

    def assemble(receipts):
        selected, conflicts = select(receipts, expected)
        # A forged valid flag cannot cause malformed data to crash assembly.
        usable = {k: v for k, v in selected.items() if isinstance(v, dict) and set(v) == set(expected[k])}
        try:
            result = ledger(usable, tasks)
        except (KeyError, TypeError):
            result = ledger({}, tasks)
            conflicts.extend(selected)
        return artifact({**result, "assembly_conflicts": sorted(set(conflicts))})

    def grade_final(result):
        value = value_of(result)
        passed = (isinstance(value, dict) and not value.get("assembly_conflicts")
                  and all(equal(value.get(k), v) for k, v in final.items()))
        return {"passed": passed, "expected_orders": len(order_ids), "expected_exceptions": len(final["exceptions"])}

    return WorkloadCase(definition["case_id"], definition["title"], definition["objective"], materials, tasks,
                        {k: artifact(v) for k, v in expected.items()}, grade_task, assemble, grade_final)
