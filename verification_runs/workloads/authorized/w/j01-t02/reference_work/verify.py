import json
import sys

from order_service import Order

def run_scenario(step):
    order = Order(step["total_cents"])
    for i, action in enumerate(step["actions"]):
        op = action["op"]
        try:
            if op == "refund":
                order.refund(action["amount"])
            elif op == "capture":
                order.capture()
            elif op == "cancel":
                order.cancel()
            else:
                raise AssertionError("unknown op %r" % op)
        except ValueError:
            return {"error": "ValueError", "at_step": i}
        else:
            # If the expected marks an error, an op that unexpectedly succeeded is a mismatch.
            pass
    return order.summary()

def main():
    with open(sys.argv[1] if len(sys.argv) > 1 else "scenarios.json") as fh:
        data = json.load(fh)

    if set(data.keys()) != {"scenarios"}:
        raise AssertionError("top-level keys must be exactly {'scenarios'}: %r" % sorted(data))

    scenarios = data["scenarios"]
    assert isinstance(scenarios, list) and scenarios, "scenarios must be a non-empty list"

    ok = 0
    for idx, step in enumerate(scenarios):
        assert set(step.keys()) == {"total_cents", "actions", "expected"}, (
            "scenario %d keys: %r" % (idx, sorted(step.keys())))
        assert isinstance(step["total_cents"], int) and not isinstance(step["total_cents"], bool)
        assert isinstance(step["actions"], list) and len(step["actions"]) <= 12, (
            "scenario %d action count out of range" % idx)
        for a in step["actions"]:
            assert a["op"] in ("capture", "cancel", "refund"), a
            if a["op"] == "refund":
                assert "amount" in a and isinstance(a["amount"], int) and not isinstance(a["amount"], bool), a
            else:
                assert set(a.keys()) == {"op"}, a

        actual = run_scenario(step)
        if actual == step["expected"]:
            ok += 1
        else:
            print("MISMATCH scenario %d:" % idx)
            print("  expected:", step["expected"])
            print("  actual  :", actual)
            return 1

    print("All %d scenarios match the correct Order implementation." % ok)
    return 0

if __name__ == "__main__":
    sys.exit(main())
