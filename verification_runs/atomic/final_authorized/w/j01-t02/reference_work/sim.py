import json, sys
sys.path.insert(0,'/workspace/reference_work')
from order_service import Order

def run(scenario):
    o = Order(scenario["total_cents"])
    for i,a in enumerate(scenario["actions"]):
        try:
            if a["op"]=="capture": o.capture()
            elif a["op"]=="cancel": o.cancel()
            elif a["op"]=="refund": o.refund(a["amount"])
            else: raise ValueError("bad op")
        except ValueError:
            return {"error":"ValueError","at_step":i}
    return o.summary()

sc = {"total_cents":1000,"actions":[{"op":"capture"},{"op":"refund","amount":0}],"expected":{"error":"ValueError","at_step":1}}
got = run(sc)
print(json.dumps(got))
assert got == sc["expected"], (got, sc["expected"])
print("OK")
