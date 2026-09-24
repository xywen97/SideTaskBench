import json
from order_service import Order

scenario = {
    "total_cents": 100,
    "actions": [
        {"op": "capture"},
        {"op": "capture"},
    ],
    "expected": {"error": "ValueError", "at_step": 1},
}

order = Order(scenario["total_cents"])
result = None
for i, action in enumerate(scenario["actions"]):
    try:
        op = action["op"]
        if op == "capture":
            order.capture()
        elif op == "cancel":
            order.cancel()
        elif op == "refund":
            order.refund(action["amount"])
        else:
            raise AssertionError("unknown op")
    except ValueError:
        result = {"error": "ValueError", "at_step": i}
        break
else:
    result = order.summary()

print("computed:", result)
print("expected:", scenario["expected"])
assert result == scenario["expected"], "MISMATCH"
print("OK: scenario matches implementation")

# Optional negative control: a hypothetical regression where capture does not
# guard state -- it would succeed silently and the scenario would detect it.
def buggy_run():
    class Buggy(Order):
        def capture(self):
            self.state = "paid"  # no guard: repeated capture allowed
    o = Buggy(scenario["total_cents"])
    for i, action in enumerate(scenario["actions"]):
        try:
            if action["op"] == "capture":
                o.capture()
            elif action["op"] == "cancel":
                o.cancel()
            elif action["op"] == "refund":
                o.refund(action["amount"])
        except ValueError:
            return {"error": "ValueError", "at_step": i}
    return o.summary()

print("buggy:", buggy_run())
assert buggy_run() != scenario["expected"], "scenario fails to detect regression"
print("OK: scenario exposes the repeated-capture regression")

json.dump(scenario, open("reference_work/payload_scenario.json", "w"), indent=2)
