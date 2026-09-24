"""Multi-source order settlement, with generated private accounting truth."""

from __future__ import annotations

import copy
import csv
import io
import json
import random

from ..contracts import WorkloadCase


CASE_ID = "order-reconciliation"


def _json(value):
    return {"kind": "json", "value": copy.deepcopy(value)}


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((_canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _same(left, right):
    try:
        return json.dumps(_canonical(left), sort_keys=True, allow_nan=False) == json.dumps(_canonical(right), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return False


def _csv(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _summary(rows):
    fields = ("expected_cents", "gross_paid_cents", "refund_cents", "net_cents")
    if any(not isinstance(row, dict) or any(type(row.get(field)) is not int for field in fields) for row in rows):
        return {"error": "invalid monetary rows"}
    return {"currency": "USD", "order_count": len(rows), **{
        field: sum(row[field] for row in rows) for field in fields}}


def _value(artifact):
    if not isinstance(artifact, dict) or artifact.get("kind") != "json" or not isinstance(artifact.get("value"), dict):
        return None
    try:
        json.dumps(artifact["value"], sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return None
    return artifact["value"]


def build_case(seed=0) -> WorkloadCase:
    rng = random.Random(seed)
    token = f"{seed % 10000:04d}"
    batches = ("web", "marketplace", "partner")
    orders, payments, refunds = [], [], []
    amounts = [rng.randrange(8, 160) * 100 + rng.choice((0, 25, 49, 99)) for _ in range(9)]
    # The business states are created before serialization. Truth follows the
    # generated transactions, not values supplied by a candidate artifact.
    for index, amount in enumerate(amounts):
        orders.append({"row_id": f"O{token}-{index + 1:02d}", "order_id": f"ORD-{token}-{index + 1:02d}",
                       "batch": batches[index // 3], "currency": "USD", "amount_cents": amount})

    def payment(index, amount, status="succeeded", suffix="a", duplicate=False):
        order_id = orders[index]["order_id"] if index is not None else f"ORD-{token}-UNKNOWN"
        key = f"{index + 1:02d}" if index is not None else "orphan"
        row = {"row_id": f"P{token}-{len(payments) + 1:02d}", "event_id": f"PE-{token}-{key}-{suffix}",
               "payment_id": f"PAY-{token}-{key}-{suffix}", "order_id": order_id,
               "currency": "USD", "amount_cents": amount, "status": status}
        payments.append(row)
        if duplicate:
            payments.append({**row, "row_id": f"P{token}-{len(payments) + 1:02d}"})
        return row["payment_id"]

    paid_ids = {}
    for index in range(9):
        status = "failed" if index == 2 else "pending" if index == 7 else "succeeded"
        paid_ids[index] = payment(index, amounts[index] - 123 if index == 8 else amounts[index],
                                  status, duplicate=index == 3)
        if index == 4:
            payment(index, amounts[index], suffix="b")
    payment(None, rng.randrange(10, 40) * 100)

    def refund(index, amount, status="succeeded", duplicate=False):
        key = f"{index + 1:02d}" if index is not None else "orphan"
        row = {"row_id": f"R{token}-{len(refunds) + 1:02d}", "event_id": f"RE-{token}-{key}",
               "refund_id": f"REF-{token}-{key}", "payment_id": paid_ids.get(index, f"PAY-{token}-MISSING"),
               "order_id": orders[index]["order_id"] if index is not None else f"ORD-{token}-UNKNOWN",
               "currency": "USD", "amount_cents": amount, "status": status}
        refunds.append(row)
        if duplicate:
            refunds.append({**row, "row_id": f"R{token}-{len(refunds) + 1:02d}"})

    refund(1, amounts[1] // 3, duplicate=True)
    refund(5, amounts[5])
    refund(6, amounts[6] + 175)
    refund(0, 100, "failed")
    refund(8, 100, "pending")
    refund(None, 225)

    truth = []
    for index, order in enumerate(orders):
        related_payments = [row for row in payments if row["order_id"] == order["order_id"]]
        related_refunds = [row for row in refunds if row["order_id"] == order["order_id"]]
        unique_payments = {row["event_id"]: row for row in related_payments}
        unique_refunds = {row["event_id"]: row for row in related_refunds}
        successes = {row["payment_id"]: row for row in unique_payments.values() if row["status"] == "succeeded"}
        successful_refunds = {row["refund_id"]: row for row in unique_refunds.values()
                              if row["status"] == "succeeded" and row["payment_id"] in successes}
        gross = sum(row["amount_cents"] for row in successes.values())
        refunded = sum(row["amount_cents"] for row in successful_refunds.values())
        flags = []
        for condition, name in (
            (gross < order["amount_cents"], "underpaid"),
            (gross > order["amount_cents"], "overpaid"),
            (len(successes) > 1, "multiple_successful_payments"),
            (refunded > gross, "over_refunded"),
            (any(row["status"] == "failed" for row in related_payments), "payment_failed"),
            (any(row["status"] == "pending" for row in related_payments), "payment_pending"),
            (any(row["status"] == "failed" for row in related_refunds), "refund_failed"),
            (any(row["status"] == "pending" for row in related_refunds), "refund_pending"),
            (len(related_payments) != len(unique_payments) or len(related_refunds) != len(unique_refunds), "duplicate_delivery"),
        ):
            if condition:
                flags.append(name)
        state = ("unpaid" if gross == 0 else "over_refunded" if refunded > gross else
                 "fully_refunded" if refunded == gross else "partially_refunded" if refunded else
                 "underpaid" if gross < order["amount_cents"] else "overpaid" if gross > order["amount_cents"] else "paid")
        truth.append({"order_id": order["order_id"], "batch": order["batch"], "currency": "USD",
                      "expected_cents": order["amount_cents"], "gross_paid_cents": gross,
                      "refund_cents": refunded, "net_cents": gross - refunded,
                      "state": state, "anomalies": sorted(flags), "payment_ids": sorted(successes),
                      "refund_ids": sorted(successful_refunds),
                      "source_rows": sorted([order["row_id"], *[row["row_id"] for row in related_payments + related_refunds]])})
    exceptions = [{"code": code, "event_id": row["event_id"], "source_rows": [row["row_id"]]}
                  for code, table in (("orphan_payment", payments), ("orphan_refund", refunds))
                  for row in table if row["order_id"].endswith("UNKNOWN")]
    expected_parts = {}
    tasks = []
    for batch in batches:
        task_id = "reconcile-" + batch
        rows = [row for row in truth if row["batch"] == batch]
        expected_parts[task_id] = {"batch": batch, "orders": rows, "summary": _summary(rows),
                                   "exceptions": exceptions if batch == "partner" else []}
        tasks.append({"task_id": task_id, "title": f"Reconcile the {batch} settlement batch", "artifact_kind": "json",
                      "description": f"Reconcile all orders with batch={batch} using all three raw tables. Return the batch JSON described in README.md.",
                      "requirements": "Use integer cents; distinguish event redelivery from a distinct successful payment; retain every physical source row reference. The partner batch owns orphan-event exceptions. Return computed rows and totals, not code.",
                      "optional": False, "material_paths": ["README.md", "data/orders.csv", "data/payments.csv", "data/refunds.csv"]})
    findings = [{"subject_id": row["order_id"], "codes": row["anomalies"], "source_rows": row["source_rows"]}
                for row in truth if row["anomalies"]]
    findings += [{"subject_id": item["event_id"], "codes": [item["code"]], "source_rows": item["source_rows"]}
                 for item in exceptions]
    optional_id = "investigate-settlement-anomalies"
    expected_parts[optional_id] = {"findings": findings}
    tasks.append({"task_id": optional_id, "title": "Prepare optional exception evidence", "artifact_kind": "json",
                  "description": "Produce an evidence index for every anomalous order and orphan event, using the findings schema in README.md.",
                  "requirements": "List exact anomaly codes and supporting physical row IDs. This investigation is optional; settlement completion depends on the ledger itself.",
                  "optional": True, "material_paths": ["README.md", "data/orders.csv", "data/payments.csv", "data/refunds.csv"]})
    references = {task_id: _json(value) for task_id, value in expected_parts.items()}
    expected_final = {"orders": truth, "summary": _summary(truth), "exceptions": exceptions}
    mandatory = {task["task_id"] for task in tasks if not task["optional"]}

    def grade_task(task_id, artifact):
        value = _value(artifact)
        expected = expected_parts.get(task_id) if isinstance(task_id, str) else None
        errors = []
        if expected is None:
            errors.append("Unknown task")
        elif value is None:
            errors.append("Expected a JSON object artifact")
        else:
            errors += [field + " differs from the required reconciliation" for field in expected
                       if not _same(value.get(field), expected[field])]
        return {"passed": not errors, "errors": errors, "checks": len(expected or {})}

    def assemble(receipts):
        selected, conflicts, seen = {}, [], set()
        for receipt in receipts:
            if (not isinstance(receipt, dict) or receipt.get("valid") is not True
                    or not isinstance(receipt.get("task_id"), str) or receipt["task_id"] not in expected_parts):
                continue
            task_id, artifact = receipt["task_id"], receipt.get("artifact")
            if task_id in selected:
                if not _same(selected[task_id], artifact) and task_id in mandatory:
                    conflicts.append({"task_id": task_id, "reason": "conflicting_submission"})
                continue
            selected[task_id] = copy.deepcopy(artifact)
        rows, exception_rows = {}, {}
        for task_id in sorted(mandatory & selected.keys()):
            value = _value(selected[task_id])
            if value is None or not isinstance(value.get("orders"), list) or not isinstance(value.get("exceptions"), list):
                conflicts.append({"task_id": task_id, "reason": "invalid_artifact"})
                continue
            for row in value["orders"]:
                if not isinstance(row, dict) or not isinstance(row.get("order_id"), str):
                    conflicts.append({"task_id": task_id, "reason": "invalid_order"})
                    continue
                key = row["order_id"]
                if key in rows:
                    conflicts.append({"order_id": key, "reason": "overlapping_order_ownership"})
                else:
                    rows[key] = copy.deepcopy(row)
            for item in value["exceptions"]:
                key = json.dumps(_canonical(item), sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    exception_rows[key] = copy.deepcopy(item)
        ordered = [rows[key] for key in sorted(rows)]
        return _json({"orders": ordered, "summary": _summary(ordered),
                      "exceptions": list(exception_rows.values()), "assembly_conflicts": conflicts,
                      "optional_evidence": _value(selected.get(optional_id))})

    def grade_final(artifact):
        value = _value(artifact)
        errors = ["Expected a JSON object artifact"] if value is None else [
            field + " fails the independent whole-ledger check" for field in expected_final
            if not _same(value.get(field), expected_final[field])]
        if value is not None and value.get("assembly_conflicts"):
            errors.append("Conflicting or overlapping mandatory contributions")
        return {"passed": not errors, "errors": errors, "expected_orders": len(truth),
                "requires_optional_investigation": False}

    specification = """# Order settlement reconciliation

The three CSV tables contain USD amounts in integer cents. Reconcile every order;
do not return a program. The order table is the authoritative expected charge.
Rows are intentionally shuffled. `row_id` identifies a physical source row.

Deduplicate payment/refund deliveries separately by event_id. Repeated deliveries
have the same business payload and must remain in source_rows. Count only status
succeeded; failed and pending events have zero monetary effect. A distinct
successful payment_id is real cash even when another payment paid the same order.
A successful refund counts only if its payment_id is a successful payment for
the same existing order. Unknown-order payment/refund events are orphan_payment /
orphan_refund exceptions, excluded from totals and owned by the partner batch.

For each order output: order_id, batch, currency, expected_cents, gross_paid_cents,
refund_cents, net_cents (= gross minus refunds), state, anomalies, payment_ids,
refund_ids, source_rows. payment_ids/refund_ids list monetary-effect transactions;
source_rows includes the order row and ALL related payment/refund physical rows,
including redeliveries, pending and failed events.

Anomalies are all applicable codes: underpaid if gross < expected; overpaid if
gross > expected; multiple_successful_payments if more than one distinct
successful payment_id; over_refunded if refunds > gross; payment_failed,
payment_pending, refund_failed, refund_pending when the corresponding status
exists; duplicate_delivery when any payment/refund event_id repeats.

State uses this priority: gross=0 -> unpaid; refunds>gross -> over_refunded;
refunds=gross -> fully_refunded; refunds>0 -> partially_refunded; gross<expected
-> underpaid; gross>expected -> overpaid; otherwise paid.

Each batch artifact is {"kind":"json","value":{"batch":BATCH,"orders":[...],
"summary":{"currency":"USD","order_count":N,"expected_cents":INT,
"gross_paid_cents":INT,"refund_cents":INT,"net_cents":INT},"exceptions":[...]}}.
Exception objects contain code, event_id and source_rows. Other batches return
an empty exceptions list. Totals sum the batch orders; never sum currencies.
Arrays may be in any order but contain no repeated rows, IDs or anomaly codes.

Optional investigation artifact: {"kind":"json","value":{"findings":[
{"subject_id":ORDER_OR_ORPHAN_EVENT_ID,"codes":[...],"source_rows":[...]}]}}.
Include every anomalous order and orphan event. This evidence index does not
replace any ledger batch and is not required to finish the final ledger.

The final deliverable combines the orders, global summary and all exceptions.
Every order appears exactly once; a batch's presence alone is not correctness.
"""
    shuffled = [copy.deepcopy(table) for table in (orders, payments, refunds)]
    for table in shuffled:
        rng.shuffle(table)
    return WorkloadCase(case_id=CASE_ID, title="Multi-source order and funds reconciliation",
                        objective="Produce an auditable USD settlement ledger across web, marketplace and partner orders, with cash totals and exceptions.",
                        public_files={"README.md": specification, **dict(zip(
                            ("data/orders.csv", "data/payments.csv", "data/refunds.csv"), map(_csv, shuffled)))},
                        tasks=tasks, reference_artifacts=references, grade_task=grade_task,
                        assemble=assemble, grade_final=grade_final)
