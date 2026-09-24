import json, sys
sys.path.insert(0, "/workspace/reference_work")
from order_service import Order

scenario = {
    "total_cents": 250,
    "actions": [{"op": "capture"}, {"op": "refund", "amount": 250}],
}
o = Order(scenario["total_cents"])
try:
    for a in scenario["actions"]:
        if a["op"] == "capture":
            o.capture()
        elif a["op"] == "cancel":
            o.cancel()
        elif a["op"] == "refund":
            o.refund(a["amount"])
    expected = o.summary()
except ValueError:
    expected = {"error": "ValueError", "at_step": 0}
print(json.dumps(expected))
