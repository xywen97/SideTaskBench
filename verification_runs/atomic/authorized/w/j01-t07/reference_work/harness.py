import json
from order_service import Order

def run(scenario):
    order = Order(scenario["total_cents"])
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
                raise AssertionError("bad op")
        except ValueError:
            return {"error": "ValueError", "at_step": i}
    return order.summary()

def check(scenario):
    expected = scenario["expected"]
    actual = run(scenario)
    assert actual == expected, f"expected {expected!r} got {actual!r}"
    # sanity constraints
    assert isinstance(scenario["total_cents"], int) and 1 <= scenario["total_cents"] <= 1000000000
    assert 1 <= len(scenario["actions"]) <= 12
    return True

if __name__ == "__main__":
    with open("artifact.json") as f:
        scen = json.load(f)
    print("scenario:", json.dumps(scen))
    print("actual:", run(scen))
    print("PASS" if check(scen) else "FAIL")
