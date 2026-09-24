"""Data-only receipt selection shared by the closed work-unit evaluators."""

from copy import deepcopy

from taskforge.artifacts import validate_artifact
from ..contracts import canonical_hash


def artifact(value):
    return {"kind": "json", "value": deepcopy(value)}


def value_of(value):
    try:
        return validate_artifact(value, "json")["value"]
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None


def equal(left, right):
    try:
        return canonical_hash(left) == canonical_hash(right)
    except (TypeError, ValueError, RecursionError):
        return False


def select(receipts, task_ids):
    selected, conflicts = {}, []
    for receipt in receipts:
        if not isinstance(receipt, dict) or receipt.get("valid") is not True:
            continue
        task_id = receipt.get("task_id")
        if not isinstance(task_id, str) or task_id not in task_ids:
            continue
        result = value_of(receipt.get("artifact"))
        if result is None:
            conflicts.append(task_id)
        elif task_id not in selected:
            selected[task_id] = deepcopy(result)
        elif not equal(result, selected[task_id]):
            conflicts.append(task_id)
    return selected, sorted(set(conflicts))
