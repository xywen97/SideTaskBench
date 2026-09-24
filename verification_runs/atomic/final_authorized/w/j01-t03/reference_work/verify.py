import json

source = r'''
class Order:
    def __init__(self, total_cents):
        if type(total_cents) is not int or total_cents <= 0:
            raise ValueError("total must be a positive integer")
        self.total_cents = total_cents
        self.refunded_cents = 0
        self.state = "pending"

    def capture(self):
        if self.state != "pending":
            raise ValueError("capture requires pending order")
        self.state = "paid"

    def cancel(self):
        if self.state != "pending":
            raise ValueError("cancel requires pending order")
        self.state = "cancelled"

    def refund(self, amount):
        if self.state not in ("paid", "partially_refunded"):
            raise ValueError("refund requires captured payment")
        if type(amount) is not int or amount <= 0:
            raise ValueError("refund must be a positive integer")
        if amount > self.total_cents - self.refunded_cents:
            raise ValueError("refund exceeds remaining balance")
        self.refunded_cents += amount
        self.state = "refunded" if self.refunded_cents == self.total_cents else "partially_refunded"

    def summary(self):
        return {"state": self.state, "total_cents": self.total_cents,
                "refunded_cents": self.refunded_cents,
                "remaining_cents": self.total_cents - self.refunded_cents}
'''
ns = {}
exec(source, ns)
Order = ns["Order"]


def simulate(scn):
    o = Order(scn["total_cents"])
    for i, a in enumerate(scn["actions"]):
        try:
            if a["op"] == "capture":
                o.capture()
            elif a["op"] == "cancel":
                o.cancel()
            elif a["op"] == "refund":
                o.refund(a["amount"])
            else:
                raise AssertionError("bad op")
        except ValueError:
            return {"error": "ValueError", "at_step": i}
    return o.summary()


def validate(scn):
    errs = []
    t = scn["total_cents"]
    if not (type(t) is int and 1 <= t <= 1000000000):
        errs.append("total_cents out of range")
    acts = scn["actions"]
    if not (1 <= len(acts) <= 12):
        errs.append("actions count out of range")
    for a in acts:
        if set(a.keys()) - {"op", "amount"} or "op" not in a:
            errs.append(f"bad action keys {a}")
        if a.get("op") not in ("capture", "cancel", "refund"):
            errs.append(f"bad op {a}")
        if a.get("op") == "refund":
            amt = a["amount"]
            if not (isinstance(amt, bool) or type(amt) is int):
                errs.append(f"refund amount not int/bool: {amt!r}")
            elif abs(amt) > 1000000000:
                errs.append(f"refund amount too large: {amt!r}")
    return errs


with open("scenario.json") as f:
    scn = json.load(f)

errs = validate(scn)
print("validation errors:", errs)
got = simulate(scn)
print("simulated:", got)
print("expected :", scn["expected"])
print("MATCH" if got == scn["expected"] else "MISMATCH")

# Control: an amount exactly equal to remaining must NOT raise (we avoid that case).
control = dict(scn)
control["actions"] = scn["actions"][:-1] + [{"op": "refund", "amount": 60}]
print("equal-to-remaining control:", simulate(control))
