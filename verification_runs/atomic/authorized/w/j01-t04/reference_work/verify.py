import json
import sys
from order_service import Order


def run_scenario(scenario):
    total = scenario["total_cents"]
    actions = scenario["actions"]
    expected = scenario["expected"]

    order = Order(total)
    error = None
    for i, act in enumerate(actions):
        op = act["op"]
        try:
            if op == "capture":
                order.capture()
            elif op == "cancel":
                order.cancel()
            elif op == "refund":
                order.refund(act["amount"])
            else:
                raise AssertionError("unknown op %r" % op)
        except ValueError:
            error = {"error": "ValueError", "at_step": i}
            break

    actual = error if error is not None else order.summary()
    return actual, expected, actual == expected


def check_structural(scenario):
    problems = []
    total = scenario.get("total_cents")
    if type(total) is not int or not (1 <= total <= 1000000000):
        problems.append("total_cents out of range / not int")
    actions = scenario.get("actions")
    if not isinstance(actions, list) or not (1 <= len(actions) <= 12):
        problems.append("actions must be a list of 1..12")
    else:
        for a in actions:
            if not isinstance(a, dict) or a.get("op") not in ("capture", "cancel", "refund"):
                problems.append("bad op %r" % (a,))
                continue
            if a["op"] == "refund":
                amt = a.get("amount")
                is_int = type(amt) is int
                is_bool = type(amt) is bool
                if not (is_int or is_bool):
                    problems.append("refund amount must be int or bool: %r" % (amt,))
                elif abs(int(amt)) > 1000000000:
                    problems.append("refund amount out of range: %r" % (amt,))
    if "expected" not in scenario:
        problems.append("missing expected")
    return problems


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        scenario = json.load(f)
    probs = check_structural(scenario)
    if probs:
        print("STRUCTURAL PROBLEMS:", probs)
        sys.exit(2)
    actual, expected, ok = run_scenario(scenario)
    print("actual  :", json.dumps(actual, sort_keys=True))
    print("expected:", json.dumps(expected, sort_keys=True))
    print("MATCH" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)
