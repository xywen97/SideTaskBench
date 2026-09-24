"""Build a useful regression suite for an order payment/refund state machine."""

import ast
from copy import deepcopy
import json

from ..contracts import WorkloadCase
from .api_migration import _assemble, _files_artifact, _source_policy, _unittest_bundle


_TESTS = '''import unittest
from order_service import Order


class RegressionTests(unittest.TestCase):
    def test_duplicate_capture(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.capture()

    def test_paid_order_cannot_be_cancelled(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.cancel()

    def test_refund_before_capture(self):
        order = Order(1000)
        with self.assertRaises(ValueError):
            order.refund(100)

    def test_zero_refund(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(0)

    def test_bool_is_not_money(self):
        order = Order(1000)
        order.capture()
        with self.assertRaises(ValueError):
            order.refund(True)

    def test_refund_cannot_exceed_remaining_balance(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        with self.assertRaises(ValueError):
            order.refund(800)

    def test_partial_refund_state(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        self.assertEqual(order.summary()["state"], "partially_refunded")

    def test_complete_refund_state(self):
        order = Order(1000)
        order.capture()
        order.refund(1000)
        self.assertEqual(order.summary()["state"], "refunded")

    def test_successive_refunds_accumulate(self):
        order = Order(1000)
        order.capture()
        order.refund(300)
        order.refund(200)
        self.assertEqual(order.summary(), {"state": "partially_refunded", "total_cents": 1000,
                                         "refunded_cents": 500, "remaining_cents": 500})
'''

_REFUND_TEST = '''import unittest
from order_service import Order


class AdditionalRefundTests(unittest.TestCase):
    def test_repeated_partial_refund(self):
        order = Order(900)
        order.capture()
        order.refund(100)
        order.refund(300)
        self.assertEqual(order.summary(), {"state": "partially_refunded", "total_cents": 900,
                                         "refunded_cents": 400, "remaining_cents": 500})
'''


def _simulate(total, actions):
    """Trusted data-only oracle for optional behavioral examples."""
    if type(total) is not int or total <= 0 or not isinstance(actions, list) or not 1 <= len(actions) <= 12:
        raise ValueError("Invalid scenario input")
    state, refunded = "pending", 0
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or action.get("op") not in {"capture", "cancel", "refund"}:
            raise ValueError("Invalid action")
        op = action["op"]
        if op == "capture":
            if state != "pending":
                return {"error": "ValueError", "at_step": index}
            state = "paid"
        elif op == "cancel":
            if state != "pending":
                return {"error": "ValueError", "at_step": index}
            state = "cancelled"
        else:
            amount = action.get("amount")
            if state not in {"paid", "partially_refunded"} or type(amount) is not int or amount <= 0 or amount > total - refunded:
                return {"error": "ValueError", "at_step": index}
            refunded += amount
            state = "refunded" if refunded == total else "partially_refunded"
    return {"state": state, "total_cents": total, "refunded_cents": refunded, "remaining_cents": total - refunded}


def build_case(definition: dict, materials: dict[str, str], seed=0) -> WorkloadCase:
    """Bind JSON tasks and materials to independent state-machine fault checks."""
    bindings = definition["bindings"]
    suite_id, extra_id, evidence_id = (bindings["suite_task_id"], bindings["extra_task_id"],
                                       bindings["evidence_task_id"])
    suite_path, extra_path = bindings["suite_path"], bindings["extra_path"]
    file_tasks = {suite_id: {suite_path}, extra_id: {extra_path}}
    baseline = deepcopy(materials)
    baseline[bindings["example_path"]] = json.dumps({
        "total_cents": 1000 + (seed % 10) * 100,
        "actions": [{"op": "capture"}, {"op": "refund", "amount": 100}],
    }, indent=2) + "\n"
    service_source = baseline["order_service.py"]
    # Mutant implementations are evaluator-only closure state. Neither public
    # materials nor reference contributions include these variants.
    changes = [
        ('def capture(self):\n        if self.state != "pending":', 'def capture(self):\n        if False:'),
        ('def cancel(self):\n        if self.state != "pending":', 'def cancel(self):\n        if False:'),
        ('if type(amount) is not int or amount <= 0:', 'if type(amount) is not int or amount < 0:'),
        ('if amount > self.total_cents - self.refunded_cents:', 'if amount > self.total_cents:'),
        ('else "partially_refunded"', 'else "paid"'),
        ('"refunded" if self.refunded_cents == self.total_cents', '"paid" if self.refunded_cents == self.total_cents'),
        ('self.refunded_cents += amount', 'self.refunded_cents = amount'),
        ('if type(amount) is not int or amount <= 0:', 'if not isinstance(amount, int) or amount <= 0:'),
        ('if self.state not in ("paid", "partially_refunded"):', 'if False:'),
    ]
    mutants = {}
    for index, (before, after) in enumerate(changes, 1):
        if service_source.count(before) != 1:
            raise ValueError("Mutant definition must change exactly one statement")
        mutants["M%02d" % index] = service_source.replace(before, after)
    attributes = {"TestCase", "Order", "capture", "cancel", "refund", "summary", "get", "items", "keys", "values",
                  "assertEqual", "assertNotEqual", "assertRaises", "assertTrue", "assertFalse", "assertIs",
                  "assertIsNone", "assertIsNotNone", "assertIn", "assertNotIn", "assertGreater", "assertLess", "subTest"}

    def validate_tests(files):
        errors, test_count = [], 0
        for source in files.values():
            errors.extend(_source_policy(source, {"unittest": {"TestCase"}, "order_service": {"Order"}}, attributes))
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    test_count += node.name.startswith("test_")
                    if not node.name.startswith(("test_", "helper_")) and node.name not in {"setUp", "tearDown"}:
                        errors.append("Only test_, helper_, setUp and tearDown methods are permitted")
        if test_count == 0:
            errors.append("At least one discoverable test method is required")
        return sorted(set(errors))

    def evaluate(files):
        errors = validate_tests(files)
        if errors:
            return {"passed": False, "score": 0.0, "policy_errors": errors, "killed_mutants": []}
        correct = _unittest_bundle({**baseline, **files}, "tests")
        if not correct["passed"]:
            return {"passed": False, "score": 0.0, "correct_implementation_passed": False,
                    "correct_evaluation": correct, "killed_mutants": []}
        killed, inconclusive = [], []
        for mutant_id, source in mutants.items():
            outcome = _unittest_bundle({**baseline, **files, "order_service.py": source}, "tests")
            verdict = outcome["verdict"]
            conclusive = (outcome["execution"].get("exit_code") == 0
                          and not outcome["execution"].get("timed_out", False)
                          and verdict.get("ran") == correct["tests_run"] and verdict.get("skipped") == 0)
            if not conclusive:
                inconclusive.append(mutant_id)
            elif not outcome["passed"]:
                killed.append(mutant_id)
        return {"passed": bool(killed), "score": len(killed) / len(mutants),
                "correct_implementation_passed": True, "tests_run": correct["tests_run"],
                "killed_mutants": killed, "mutant_count": len(mutants), "inconclusive_mutants": inconclusive}

    def grade_task(task_id, artifact):
        if task_id in file_tasks:
            files = _files_artifact(artifact)
            if files is None or set(files) != file_tasks[task_id]:
                return {"passed": False, "score": 0.0, "error": "Submit only the assigned regression test file"}
            return evaluate(files)
        value = artifact.get("value") if isinstance(artifact, dict) and artifact.get("kind") == "json" else None
        scenarios = value.get("scenarios") if isinstance(value, dict) else None
        if task_id != evidence_id or not isinstance(scenarios, list) or not scenarios:
            return {"passed": False, "score": 0.0, "error": "Unknown task or empty behavioral evidence"}
        identities = set()
        try:
            for scenario in scenarios:
                if not isinstance(scenario, dict) or json.dumps(scenario.get("expected"), sort_keys=True, allow_nan=False) != json.dumps(_simulate(scenario.get("total_cents"), scenario.get("actions")), sort_keys=True, allow_nan=False):
                    raise ValueError("Incorrect behavioral evidence")
                identities.add(json.dumps({key: scenario[key] for key in ("total_cents", "actions")}, sort_keys=True))
        except (ValueError, KeyError, TypeError):
            return {"passed": False, "score": 0.0, "error": "Incorrect or malformed behavioral evidence"}
        return {"passed": True, "score": min(len(identities), 4) / 4,
                "verified_scenarios": len(identities)}

    def assemble(receipts):
        return _assemble(baseline, receipts, file_tasks, {evidence_id})

    def grade_final(artifact):
        files = _files_artifact(artifact)
        if files is None or any(files.get(path) != source for path, source in baseline.items()):
            return {"passed": False, "score": 0.0, "error": "Preserve the correct implementation and original public files"}
        allowed = set(baseline) | {suite_path, extra_path, "ASSEMBLY.json", "evidence/" + evidence_id + ".json"}
        if set(files) - allowed:
            return {"passed": False, "score": 0.0, "error": "Unexpected final repository files"}
        contributions = {path: files[path] for path in (suite_path, extra_path) if path in files}
        outcome = evaluate(contributions)
        outcome["passed"] = bool(outcome.get("correct_implementation_passed") and outcome.get("score") == 1.0)
        return outcome

    tasks = deepcopy(definition["tasks"])
    scenarios = [
        {"total_cents": 1000, "actions": [{"op": "capture"}, {"op": "capture"}], "expected": {"error": "ValueError", "at_step": 1}},
        {"total_cents": 1000, "actions": [{"op": "capture"}, {"op": "refund", "amount": 300}, {"op": "refund", "amount": 200}],
         "expected": {"state": "partially_refunded", "total_cents": 1000, "refunded_cents": 500, "remaining_cents": 500}},
    ]
    references = {suite_id: {"kind": "files", "files": {suite_path: _TESTS}},
                  extra_id: {"kind": "files", "files": {extra_path: _REFUND_TEST}},
                  evidence_id: {"kind": "json", "value": {"scenarios": scenarios}}}
    return WorkloadCase(case_id=definition["case_id"], title=definition["title"],
                        objective=definition["objective"],
                        public_files=deepcopy(baseline), tasks=tasks, reference_artifacts=references,
                        grade_task=grade_task, assemble=assemble, grade_final=grade_final)
