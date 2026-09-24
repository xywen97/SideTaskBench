"""Each contribution is one closed scenario; assemble an executable test suite."""

from copy import deepcopy
import json

from ..contracts import WorkloadCase
from .api_migration import _files_artifact, _unittest_bundle
from .atomic_common import artifact, equal, value_of
from .regression_tests import _simulate


MUTATIONS = [
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
REFERENCE_ACTIONS = [
    [{"op": "capture"}, {"op": "capture"}],
    [{"op": "capture"}, {"op": "cancel"}],
    [{"op": "capture"}, {"op": "refund", "amount": 0}],
    [{"op": "capture"}, {"op": "refund", "amount": 300}, {"op": "refund", "amount": 800}],
    [{"op": "capture"}, {"op": "refund", "amount": 300}],
    [{"op": "capture"}, {"op": "refund", "amount": 1000}],
    [{"op": "capture"}, {"op": "refund", "amount": 300}, {"op": "refund", "amount": 200}],
    [{"op": "capture"}, {"op": "refund", "amount": True}],
    [{"op": "refund", "amount": 100}],
]


def _valid(scenario):
    if not isinstance(scenario, dict) or set(scenario) != {"total_cents", "actions", "expected"}:
        return False
    try:
        if not (type(scenario["total_cents"]) is int and 0 < scenario["total_cents"] <= 10**9):
            return False
        if not isinstance(scenario["actions"], list) or not 1 <= len(scenario["actions"]) <= 12:
            return False
        for action in scenario["actions"]:
            if not isinstance(action, dict) or action.get("op") not in {"capture", "cancel", "refund"}:
                return False
            if action["op"] == "refund":
                if set(action) != {"op", "amount"} or type(action["amount"]) not in {int, bool} or abs(action["amount"]) > 10**9:
                    return False
            elif set(action) != {"op"}:
                return False
        return equal(scenario["expected"], _simulate(scenario["total_cents"], scenario["actions"]))
    except (ValueError, TypeError, KeyError):
        return False


def _test_source(scenarios):
    return '''import json, unittest
from order_service import Order
SCENARIOS = %r

class AtomicRegressionTests(unittest.TestCase):
    def test_scenarios(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                order = Order(scenario["total_cents"])
                actual = None
                for index, action in enumerate(scenario["actions"]):
                    try:
                        if action["op"] == "capture": order.capture()
                        elif action["op"] == "cancel": order.cancel()
                        else: order.refund(action["amount"])
                    except ValueError:
                        actual = {"error": "ValueError", "at_step": index}
                        break
                if actual is None: actual = order.summary()
                self.assertEqual(json.dumps(actual, sort_keys=True), json.dumps(scenario["expected"], sort_keys=True))
''' % scenarios


def build_case(definition, materials, seed=0):
    tasks = deepcopy(definition["tasks"])
    targets = definition["bindings"]["mutant_targets"]
    if set(targets) != {t["task_id"] for t in tasks} or set(targets.values()) != {"M%02d" % i for i in range(1, 10)}:
        raise ValueError("One closed scenario task is required for each of the nine fault families")
    sources = {t["packet"]["input"]["source"] for t in tasks}
    if len(sources) != 1:
        raise ValueError("All independent packets must specify the same public Order contract")
    source = next(iter(sources))
    mutants = {}
    for i, (before, after) in enumerate(MUTATIONS, 1):
        if source.count(before) != 1:
            raise ValueError("A fault must alter one public implementation statement")
        mutants["M%02d" % i] = source.replace(before, after)

    def evaluate(scenarios, selected_mutants):
        if not scenarios or not all(_valid(s) for s in scenarios):
            return {"passed": False, "error": "Supply correct, nonempty scenarios within the packet contract", "killed_mutants": []}
        tests = _test_source(scenarios)
        correct = _unittest_bundle({"order_service.py": source, "tests/test_atomic.py": tests}, "tests")
        if not correct["passed"]:
            return {"passed": False, "correct_implementation_passed": False, "killed_mutants": []}
        killed, inconclusive = [], []
        for mutant in selected_mutants:
            outcome = _unittest_bundle({"order_service.py": mutants[mutant], "tests/test_atomic.py": tests}, "tests")
            verdict = outcome["verdict"]
            if (outcome["execution"].get("exit_code") != 0 or outcome["execution"].get("timed_out")
                    or verdict.get("ran") != correct["tests_run"] or verdict.get("skipped") != 0):
                inconclusive.append(mutant)
            elif not outcome["passed"]:
                killed.append(mutant)
        return {"passed": len(killed) == len(selected_mutants), "correct_implementation_passed": True,
                "killed_mutants": killed, "inconclusive_mutants": inconclusive, "score": len(killed) / len(selected_mutants)}

    def grade_task(task_id, result):
        if task_id not in targets:
            return {"passed": False, "error": "Unknown work unit"}
        return evaluate([value_of(result)], [targets[task_id]])

    def assemble(receipts):
        # Multiple correct examples of one behavior are alternatives, not
        # contradictory facts. Select the first accepted scenario per task and
        # retain every alternative's receipt identity in the assembly record.
        selected, entries = {}, []
        for receipt in receipts:
            if not isinstance(receipt, dict):
                continue
            task_id = receipt.get("task_id")
            if not isinstance(task_id, str) or task_id not in targets or receipt.get("valid") is not True:
                continue
            scenario = value_of(receipt.get("artifact"))
            if not _valid(scenario):
                continue
            status = "selected" if task_id not in selected else "accepted_alternative"
            selected.setdefault(task_id, scenario)
            entries.append({"receipt_id": receipt.get("receipt_id"), "task_id": task_id, "status": status})
        scenarios = [selected[k] for k in sorted(selected)]
        return {"kind": "files", "files": {"order_service.py": source,
                "scenarios.json": json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n",
                "tests/test_atomic.py": _test_source(scenarios),
                "ASSEMBLY.json": json.dumps({"policy": "first_accepted_scenario_per_task", "conflicts": [],
                                            "task_ids": sorted(selected), "receipts": entries}, sort_keys=True) + "\n"}}

    def grade_final(result):
        files = _files_artifact(result)
        if files is None or set(files) != {"order_service.py", "scenarios.json", "tests/test_atomic.py", "ASSEMBLY.json"}:
            return {"passed": False, "error": "Incomplete test package"}
        try:
            scenarios = json.loads(files["scenarios.json"])
            metadata = json.loads(files["ASSEMBLY.json"])
            if (not isinstance(scenarios, list) or not isinstance(metadata, dict) or metadata.get("conflicts")
                    or files["order_service.py"] != source or files["tests/test_atomic.py"] != _test_source(scenarios)):
                raise ValueError("Altered test package")
        except (ValueError, TypeError):
            return {"passed": False, "error": "Invalid or conflicting test package"}
        return evaluate(scenarios, list(mutants))

    references = {}
    for task_id, target in targets.items():
        actions = deepcopy(REFERENCE_ACTIONS[int(target[1:]) - 1])
        references[task_id] = artifact({"total_cents": 1000, "actions": actions, "expected": _simulate(1000, actions)})
    return WorkloadCase(definition["case_id"], definition["title"], definition["objective"], materials, tasks,
                        references, grade_task, assemble, grade_final)
