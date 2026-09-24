"""Three portable functions compose an offline paginated SDK migration adapter."""

import ast
from copy import deepcopy
import json
import random

from ..contracts import WorkloadCase
from .api_migration import _assemble, _files_artifact, _source_policy, _unittest_bundle


REFERENCES = {
    "normalize_order": '''def normalize_order(row):
    return {"order_id": row["id"], "customer_id": row["customer"],
            "state": "settled" if row["paid"] else "pending",
            "gross_cents": row["amount"], "refund_cents": row["refunded"]}
''',
    "collect_orders": '''def collect_orders(pages, start_token):
    result, seen = [], set()
    token = start_token
    while token is not None:
        if token in seen or token not in pages:
            raise ValueError("Invalid page chain")
        seen.add(token)
        page = pages[token]
        result.extend(page["orders"])
        token = page["next"]
    return result
''',
    "customer_totals": '''def customer_totals(rows, customer_id):
    selected = [row for row in rows if row["customer_id"] == customer_id and row["state"] == "settled"]
    return {"customer_id": customer_id, "order_count": len(selected),
            "net_cents": sum(row["gross_cents"] - row["refund_cents"] for row in selected)}
''',
}
PIPELINE = '''from normalize_order import normalize_order
from collect_orders import collect_orders
from customer_totals import customer_totals


def statement(pages, start_token, customer_id):
    return customer_totals([normalize_order(row) for row in collect_orders(pages, start_token)], customer_id)
'''
ATTRIBUTES = {"get", "items", "keys", "values", "append", "extend", "copy", "sort", "pop", "add"}


def _policy(source, function):
    errors = _source_policy(source, {}, ATTRIBUTES)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return errors
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != function or any(isinstance(node, ast.ClassDef) for node in ast.walk(tree)):
        errors.append("Submit exactly the assigned top-level function, without classes")
    return sorted(set(errors))


def _evaluate(files, module, function, vectors):
    driver = '''import copy, importlib, json, unittest
FUNCTION = getattr(importlib.import_module(%r), %r)
VECTORS = %r

class ContractTests(unittest.TestCase):
    def test_contract(self):
        for vector in VECTORS:
            args = copy.deepcopy(vector["args"])
            original = copy.deepcopy(args)
            if "error" in vector:
                with self.assertRaises(ValueError):
                    FUNCTION(*args)
            else:
                actual = FUNCTION(*args)
                self.assertEqual(json.dumps(actual, sort_keys=True, allow_nan=False),
                                 json.dumps(vector["expected"], sort_keys=True, allow_nan=False))
            self.assertEqual(args, original)
''' % (module, function, vectors)
    return _unittest_bundle({**files, "acceptance/test_contract.py": driver}, "acceptance")


def build_case(definition, materials, seed=0):
    tasks = deepcopy(definition["tasks"])
    functions = {t["task_id"]: t["packet"]["output"]["function"] for t in tasks}
    if set(functions.values()) != set(REFERENCES) or len(tasks) != 3:
        raise ValueError("The atomic migration requires three distinct adapter functions")
    paths = {task_id: function + ".py" for task_id, function in functions.items()}
    if any(t["packet"]["output"]["path"] != paths[t["task_id"]] for t in tasks):
        raise ValueError("Function module paths must match the adapter contract")
    rng = random.Random(seed)
    raw = [{"id": str(i), "customer": "a" if i % 3 else "b", "paid": i % 4 != 0,
            "amount": rng.randrange(1, 10000), "refunded": 0} for i in range(15)]
    for row in raw:
        row["refunded"] = rng.randrange(row["amount"] + 1)
    raw += [{"id": "zero", "customer": "a", "paid": True, "amount": 500, "refunded": 500}]
    normalized = [{"order_id": r["id"], "customer_id": r["customer"], "state": "settled" if r["paid"] else "pending",
                   "gross_cents": r["amount"], "refund_cents": r["refunded"]} for r in raw]
    totals = {c: {"customer_id": c, "order_count": sum(r["paid"] and r["customer"] == c for r in raw),
                  "net_cents": sum(r["amount"] - r["refunded"] for r in raw if r["paid"] and r["customer"] == c)}
              for c in ("a", "b", "missing")}
    pages = {"first": {"orders": raw[:3], "next": "empty"}, "empty": {"orders": [], "next": "last"},
             "last": {"orders": raw[3:], "next": None}, "unreachable": {"orders": [{"irrelevant": True}], "next": None}}
    vectors = {
        "normalize_order": [{"args": [r], "expected": n} for r, n in zip(raw, normalized)],
        "collect_orders": [{"args": [pages, "first"], "expected": raw}, {"args": [{}, None], "expected": []},
                           {"args": [{"x": {"orders": [], "next": "x"}}, "x"], "error": "ValueError"},
                           {"args": [{}, "missing"], "error": "ValueError"},
                           {"args": [{"x": {"orders": [1], "next": "missing"}}, "x"], "error": "ValueError"}],
        "customer_totals": [{"args": [normalized, c], "expected": result} for c, result in totals.items()]
                           + [{"args": [[], "a"], "expected": {"customer_id": "a", "order_count": 0, "net_cents": 0}}],
    }
    final_vectors = [{"args": [pages, "first", c], "expected": result} for c, result in totals.items()]
    final_vectors += [{"args": [{}, None, "empty"], "expected": {"customer_id": "empty", "order_count": 0, "net_cents": 0}},
                      {"args": [{"x": {"orders": [], "next": "x"}}, "x", "a"], "error": "ValueError"}]

    def grade_task(task_id, artifact):
        files = _files_artifact(artifact)
        if task_id not in paths or files is None or set(files) != {paths[task_id]}:
            return {"passed": False, "error": "Submit only the assigned function file"}
        errors = _policy(files[paths[task_id]], functions[task_id])
        if errors:
            return {"passed": False, "policy_errors": errors}
        return _evaluate(files, functions[task_id], functions[task_id], vectors[functions[task_id]])

    def assemble(receipts):
        return _assemble({"statement.py": PIPELINE}, receipts, {k: {v} for k, v in paths.items()}, set())

    def grade_final(artifact):
        files = _files_artifact(artifact)
        if (files is None or set(files) != {*paths.values(), "statement.py", "ASSEMBLY.json"}
                or files["statement.py"] != PIPELINE):
            return {"passed": False, "error": "All three contributions and the unchanged platform adapter are required"}
        errors = [e for task_id, path in paths.items() for e in _policy(files[path], functions[task_id])]
        if errors:
            return {"passed": False, "policy_errors": sorted(set(errors))}
        return _evaluate(files, "statement", "statement", final_vectors)

    references = {t: {"kind": "files", "files": {paths[t]: REFERENCES[f]}} for t, f in functions.items()}
    return WorkloadCase(definition["case_id"], definition["title"], definition["objective"], materials,
                        tasks, references, grade_task, assemble, grade_final)
