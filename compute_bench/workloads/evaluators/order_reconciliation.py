"""Multi-source order settlement, with generated private accounting truth."""

from __future__ import annotations

import copy
import csv
import io
import json
import random

from ..contracts import WorkloadCase


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


def build_case(definition: dict, materials: dict[str, str], seed=0) -> WorkloadCase:
    tasks = copy.deepcopy(definition["tasks"])
    bindings = definition["bindings"]
    rng = random.Random(seed)
    token = f"{seed % 10000:04d}"
    batch_tasks = bindings["batch_tasks"]
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
    for batch in batches:
        task_id = batch_tasks[batch]
        rows = [row for row in truth if row["batch"] == batch]
        expected_parts[task_id] = {"batch": batch, "orders": rows, "summary": _summary(rows),
                                   "exceptions": exceptions if batch == "partner" else []}
    findings = [{"subject_id": row["order_id"], "codes": row["anomalies"], "source_rows": row["source_rows"]}
                for row in truth if row["anomalies"]]
    findings += [{"subject_id": item["event_id"], "codes": [item["code"]], "source_rows": item["source_rows"]}
                 for item in exceptions]
    optional_id = bindings["investigation_task"]
    expected_parts[optional_id] = {"findings": findings}
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

    shuffled = [copy.deepcopy(table) for table in (orders, payments, refunds)]
    for table in shuffled:
        rng.shuffle(table)
    generated = dict(zip(("data/orders.csv", "data/payments.csv", "data/refunds.csv"), map(_csv, shuffled)))
    return WorkloadCase(case_id=definition["case_id"], title=definition["title"],
                        objective=definition["objective"], public_files={**materials, **generated},
                        tasks=tasks, reference_artifacts=references, grade_task=grade_task,
                        assemble=assemble, grade_final=grade_final)
