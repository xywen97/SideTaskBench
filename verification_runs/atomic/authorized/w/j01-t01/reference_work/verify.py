import json
from order_service import Order

scenario = {
    "total_cents": 5000,
    "actions": [{"op": "capture"}, {"op": "cancel"}],
    "expected": {"error": "ValueError", "at_step": 1},
}


def run(scenario, OrderCls):
    o = OrderCls(scenario["total_cents"])
    for i, action in enumerate(scenario["actions"]):
        op = action["op"]
        if op == "capture":
            o.capture()
        elif op == "cancel":
            o.cancel()
        elif op == "refund":
            o.refund(action["amount"])
        else:
            raise AssertionError("bad op")
    return o.summary()


# Validate constraints
tc = scenario["total_cents"]
assert type(tc) is int and 1 <= tc <= 1000000000, "total_cents range"
assert 1 <= len(scenario["actions"]) <= 12, "action count"
for a in scenario["actions"]:
    assert a["op"] in ("capture", "cancel", "refund")
    if a["op"] == "refund":
        amt = a["amount"]
        assert (type(amt) is int or type(amt) is bool) and abs(amt) <= 1000000000

got = None
try:
    got = {"summary": run(scenario, Order)}
except ValueError:
    # recompute at_step
    o = Order(scenario["total_cents"])
    for i, action in enumerate(scenario["actions"]):
        try:
            op = action["op"]
            if op == "capture":
                o.capture()
            elif op == "cancel":
                o.cancel()
            elif op == "refund":
                o.refund(action["amount"])
        except ValueError:
            got = {"error": "ValueError", "at_step": i}
            break

print("result:", json.dumps(got))
expected = scenario["expected"]
assert got == expected, f"MISMATCH got={got} expected={expected}"
print("MATCH: scenario matches correct implementation")


# --- Sanity: a faulty impl that allows cancelling a paid order must diverge ---
class FaultyOrder(Order):
    def cancel(self):
        # buggy: ignores state
        self.state = "cancelled"


try:
    faulty = {"summary": run(scenario, FaultyOrder)}
except ValueError:
    faulty = {"error": "ValueError"}
print("faulty result:", json.dumps(faulty))
assert faulty != expected, "faulty impl should diverge (scenario exposes regression)"
print("OK: scenario distinguishes correct vs faulty (cancel paid allowed)")
