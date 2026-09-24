"""A business application migration, with optional compatibility evidence."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import random

from ..contracts import WorkloadCase
from ..isolation import run_python


_MARKER = "__WORKLOAD_GRADE__="
_FORBIDDEN_NAMES = {
    "open", "eval", "exec", "compile", "__import__", "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "hasattr", "type", "object", "super", "help", "input",
    "breakpoint", "print", "exit", "quit", "classmethod", "staticmethod", "property",
}


def _source_policy(source, imports, attributes):
    """Constrain submitted Python to public API computation, never fixture access.

    Isolation is still mandatory. This capability policy also stops submissions
    reading the private test driver or replacing the implementation under test.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError) as exc:
        return ["Invalid Python: " + type(exc).__name__]
    errors = []
    helper_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for statement in tree.body:
        if not isinstance(statement, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)):
                errors.append("Module-level executable statements are not permitted")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in imports for alias in node.names):
                errors.append("Only the declared public modules may be imported")
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in imports or any(alias.name not in imports.get(node.module, ()) for alias in node.names):
                errors.append("Only declared public symbols may be imported")
        elif isinstance(node, ast.Name) and (node.id in _FORBIDDEN_NAMES or node.id.startswith("__")):
            errors.append("Forbidden reflective or I/O capability: " + node.id)
        elif isinstance(node, ast.Attribute):
            local_helper = isinstance(node.value, ast.Name) and node.value.id == "self" and node.attr in helper_names
            if node.attr.startswith("_") or (node.attr not in attributes and not local_helper):
                errors.append("Undeclared attribute capability: " + node.attr)
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                errors.append("Mutating object/module attributes is not permitted")
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.decorator_list or node.name.startswith("__"):
                errors.append("Decorators and special protocol definitions are not permitted")
            if isinstance(node, ast.FunctionDef) and any(not isinstance(value, ast.Constant) for value in node.args.defaults + [x for x in node.args.kw_defaults if x is not None]):
                errors.append("Function defaults must be constants")
        elif isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef)):
            errors.append("Global state mutation and asynchronous code are not permitted")
    return sorted(set(errors))


def _files_artifact(artifact):
    if not isinstance(artifact, dict) or artifact.get("kind") != "files" or not isinstance(artifact.get("files"), dict):
        return None
    files = artifact["files"]
    if not files:
        return None
    for name, source in files.items():
        if not isinstance(name, str) or not isinstance(source, str) or "\\" in name:
            return None
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or name in {".", ""}:
            return None
    return dict(files)


def _unittest_bundle(files, test_directory, *, python_path="."):
    driver = (
        "import json, sys, unittest\n"
        f"sys.path.insert(0, {python_path!r})\n"
        f"suite = unittest.defaultTestLoader.discover({test_directory!r}, pattern='test_*.py')\n"
        "result = unittest.TextTestRunner(verbosity=1).run(suite)\n"
        "verdict = {'ran': result.testsRun, 'failures': len(result.failures), "
        "'errors': len(result.errors), 'skipped': len(result.skipped), "
        "'successful': result.wasSuccessful()}\n"
        f"print({_MARKER!r} + json.dumps(verdict, sort_keys=True))\n"
    )
    execution = run_python({**files, "_workload_grade.py": driver}, "python3 _workload_grade.py", timeout=20)
    markers = [line[len(_MARKER):] for line in execution.get("stdout", "").splitlines() if line.startswith(_MARKER)]
    try:
        verdict = json.loads(markers[0]) if len(markers) == 1 else {}
    except (ValueError, TypeError):
        verdict = {}
    passed = (execution.get("exit_code") == 0 and not execution.get("timed_out", False)
              and verdict.get("successful") is True and verdict.get("ran", 0) > 0
              and verdict.get("skipped") == 0 and verdict.get("errors") == 0 and verdict.get("failures") == 0)
    return {"passed": passed, "tests_run": verdict.get("ran", 0), "verdict": verdict, "execution": execution}


def _assemble(baseline, receipts, file_tasks, json_tasks):
    """First accepted content wins; every duplicate/alternative retains provenance."""
    files, selected, entries = deepcopy(baseline), {}, []
    for index, receipt in enumerate(receipts):
        task_id = receipt.get("task_id")
        entry = {"receipt_id": receipt.get("receipt_id", "input-" + str(index)), "task_id": task_id}
        artifact = receipt.get("artifact")
        if receipt.get("valid") is not True or task_id not in file_tasks.keys() | json_tasks:
            entries.append({**entry, "status": "ignored"})
            continue
        try:
            encoded = json.dumps(artifact, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        except (ValueError, TypeError):
            entries.append({**entry, "status": "malformed"})
            continue
        entry["artifact_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
        if task_id in file_tasks:
            contribution = _files_artifact(artifact)
            if contribution is None or set(contribution) != file_tasks[task_id]:
                entries.append({**entry, "status": "malformed"})
                continue
        elif isinstance(artifact, dict) and artifact.get("kind") == "json" and "value" in artifact:
            contribution = {"evidence/" + task_id + ".json": json.dumps(artifact["value"], ensure_ascii=False, sort_keys=True, indent=2) + "\n"}
        else:
            entries.append({**entry, "status": "malformed"})
            continue
        actions = []
        for path, source in contribution.items():
            content_hash = hashlib.sha256(source.encode()).hexdigest()
            prior = selected.get(path)
            if prior is None:
                files[path] = source
                selected[path] = {**entry, "source_sha256": content_hash}
                status = "selected"
            else:
                status = "duplicate" if prior["source_sha256"] == content_hash else "conflicting_alternative"
            actions.append({"path": path, "status": status, "source_sha256": content_hash,
                            "selected_receipt_id": selected[path]["receipt_id"]})
        entries.append({**entry, "files": actions})
    files["ASSEMBLY.json"] = json.dumps({"policy": "first_valid_content_per_path", "receipts": entries}, ensure_ascii=False, indent=2) + "\n"
    return {"kind": "files", "files": files}


_MIGRATED_REPORT = '''from sdk_v2 import Ledger


def monthly_statement(rows, customer_id):
    ledger = Ledger(rows)
    token = None
    count = 0
    net = 0
    while True:
        page = ledger.page_orders(customer_id=customer_id, page_token=token, page_size=2)
        for order in page["orders"]:
            if order["state"] == "settled":
                count += 1
                net += order["gross_cents"] - order["refund_cents"]
        token = page["next_page_token"]
        if token is None:
            break
    return {"customer_id": customer_id, "order_count": count, "net_cents": net}
'''


def build_case(definition: dict, materials: dict[str, str], seed=0) -> WorkloadCase:
    """Bind JSON task metadata and public files to the private migration oracle."""
    bindings = definition["bindings"]
    patch_id, diagnosis_id = bindings["patch_task_id"], bindings["diagnosis_task_id"]
    patch_path = bindings["patch_path"]
    baseline = deepcopy(materials)
    rng = random.Random(seed)
    private_rows = [{"id": "private-" + str(i), "customer_id": "north" if i % 4 else "south",
                     "state": ("settled", "pending", "settled", "cancelled", "settled")[i % 5],
                     "gross_cents": rng.randrange(1, 50000), "refund_cents": 0} for i in range(19)]
    for row in private_rows:
        row["refund_cents"] = rng.randrange(row["gross_cents"] + 1)
    private_rows.append({"id": "fully-refunded", "customer_id": "north", "state": "settled", "gross_cents": 1234, "refund_cents": 1234})
    expected = {customer: {"customer_id": customer,
                          "order_count": sum(row["state"] == "settled" and row["customer_id"] == customer for row in private_rows),
                          "net_cents": sum(row["gross_cents"] - row["refund_cents"] for row in private_rows if row["state"] == "settled" and row["customer_id"] == customer)}
                for customer in ("north", "south", "missing")}
    private_tests = '''import copy, importlib, json, subprocess, sys, unittest
import order_report, sdk_v2

ROWS = %r
EXPECTED = %r

class Acceptance(unittest.TestCase):
    def test_paginated_business_totals(self):
        for customer, expected in EXPECTED.items():
            self.assertEqual(order_report.monthly_statement(ROWS, customer), expected)
    def test_no_input_mutation(self):
        rows = copy.deepcopy(ROWS)
        order_report.monthly_statement(rows, "north")
        self.assertEqual(rows, ROWS)
    def test_fully_refunded_still_counts(self):
        self.assertEqual(order_report.monthly_statement([ROWS[-1]], "north"),
                         {"customer_id": "north", "order_count": 1, "net_cents": 0})
    def test_cli_contract(self):
        process = subprocess.run([sys.executable, "repo/cli.py", "repo/sample_orders.json", "north"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout), {"customer_id": "north", "order_count": 1, "net_cents": 1200})
    def test_z_uses_public_sdk(self):
        original = sdk_v2.Ledger
        class Probe:
            def __init__(self, rows):
                pass
            def page_orders(self, *, customer_id, page_token=None, page_size=2):
                return {"orders": [{"state": "settled", "gross_cents": 733, "refund_cents": 33}], "next_page_token": None}
        try:
            sdk_v2.Ledger = Probe
            importlib.reload(order_report)
            self.assertEqual(order_report.monthly_statement([], "probe"),
                             {"customer_id": "probe", "order_count": 1, "net_cents": 700})
        finally:
            sdk_v2.Ledger = original
            importlib.reload(order_report)
''' % (private_rows, expected)
    attributes = {"Ledger", "page_orders", "get", "items", "keys", "values", "append", "extend", "copy", "sort", "pop"}
    changes = {
        "pagination": ("all_at_once", "next_page_token"),
        "amounts": ("net_decimal", "gross_minus_refund_cents"),
        "states": ("settled_only", "all_states"),
    }

    def grade_patch(artifact):
        files = _files_artifact(artifact)
        if files is None or set(files) != {patch_path}:
            return {"passed": False, "score": 0.0, "error": "Submit only " + patch_path}
        source = files[patch_path]
        errors = _source_policy(source, {"sdk_v2": {"Ledger"}}, attributes)
        if errors:
            return {"passed": False, "score": 0.0, "policy_errors": errors}
        bundle = {**baseline, **files, "repo/tests/test_acceptance.py": private_tests}
        verdict = _unittest_bundle(bundle, "repo/tests", python_path="repo")
        verdict["score"] = float(verdict["passed"])
        return verdict

    def grade_task(task_id, artifact):
        if task_id == patch_id:
            return grade_patch(artifact)
        value = artifact.get("value") if isinstance(artifact, dict) and artifact.get("kind") == "json" else None
        items = value.get("changes") if isinstance(value, dict) else None
        if task_id != diagnosis_id or not isinstance(items, list) or not items:
            return {"passed": False, "score": 0.0, "error": "Unknown task or empty compatibility evidence"}
        aspects = []
        for item in items:
            if not isinstance(item, dict) or item.get("aspect") not in changes or (item.get("before"), item.get("after")) != changes[item["aspect"]]:
                return {"passed": False, "score": 0.0, "error": "Unsupported compatibility claim"}
            aspects.append(item["aspect"])
        return {"passed": True, "score": len(set(aspects)) / len(changes), "verified_aspects": sorted(set(aspects))}

    def assemble(receipts):
        return _assemble(baseline, receipts, {patch_id: {patch_path}}, {diagnosis_id})

    def grade_final(artifact):
        files = _files_artifact(artifact)
        if files is None or any(files.get(path) != source for path, source in baseline.items() if path != patch_path):
            return {"passed": False, "score": 0.0, "error": "The original SDK, CLI and public tests must be preserved"}
        allowed = set(baseline) | {"ASSEMBLY.json", "evidence/" + diagnosis_id + ".json"}
        if set(files) - allowed:
            return {"passed": False, "score": 0.0, "error": "Unexpected files in final repository"}
        return grade_patch({"kind": "files", "files": {patch_path: files.get(patch_path, "")}})

    tasks = deepcopy(definition["tasks"])
    references = {
        patch_id: {"kind": "files", "files": {patch_path: _MIGRATED_REPORT}},
        diagnosis_id: {"kind": "json", "value": {"changes": [{"aspect": aspect, "before": before, "after": after} for aspect, (before, after) in changes.items()]}},
    }
    return WorkloadCase(case_id=definition["case_id"], title=definition["title"],
                        objective=definition["objective"],
                        public_files=deepcopy(baseline), tasks=tasks, reference_artifacts=references,
                        grade_task=grade_task, assemble=assemble, grade_final=grade_final)
