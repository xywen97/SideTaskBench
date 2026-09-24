import json, types
from order_service import Order

scenario = json.load(open("scenario.json"))

def run(cls):
    total = scenario["total_cents"]
    o = cls(total)
    err = None
    for i, a in enumerate(scenario["actions"]):
        try:
            if a["op"] == "capture": o.capture()
            elif a["op"] == "cancel": o.cancel()
            else: o.refund(a["amount"])
        except ValueError:
            err = {"error": "ValueError", "at_step": i}; break
    return err if err is not None else o.summary()

# Fault A: partial refund leaves state unchanged (stays "paid")
class FaultA(Order):
    def refund(self, amount):
        super().refund(amount)
        if self.refunded_cents != self.total_cents:
            self.state = "paid"

# Fault B: partial refund always marks "refunded"
class FaultB(Order):
    def refund(self, amount):
        super().refund(amount)
        self.state = "refunded"

for name, cls in (("correct", Order), ("FaultA(no-change)", FaultA), ("FaultB(always-refunded)", FaultB)):
    got = run(cls)
    print(f"{name:24} -> {json.dumps(got, sort_keys=True)}  exposed={got != scenario['expected']}")
