import importlib.util, sys

spec = importlib.util.spec_from_file_location("ct", "/workspace/customer_totals.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
customer_totals = m.customer_totals

# Example from packet
rows = [{"order_id":"o1","customer_id":"north","state":"settled","gross_cents":1200,"refund_cents":200}]
assert customer_totals(rows, "north") == {"customer_id":"north","order_count":1,"net_cents":1000}, "ex1"

# Only matching customer + settled state
rows = [
  {"order_id":"o1","customer_id":"north","state":"settled","gross_cents":1200,"refund_cents":200},
  {"order_id":"o2","customer_id":"south","state":"settled","gross_cents":500,"refund_cents":0},
  {"order_id":"o3","customer_id":"north","state":"pending","gross_cents":900,"refund_cents":0},
  {"order_id":"o4","customer_id":"north","state":"settled","gross_cents":300,"refund_cents":300},
]
r = customer_totals(rows, "north")
assert r == {"customer_id":"north","order_count":2,"net_cents":1000}, r

# Fully refunded rows still counted
rows = [{"customer_id":"north","state":"settled","gross_cents":100,"refund_cents":100}]
assert customer_totals(rows,"north") == {"customer_id":"north","order_count":1,"net_cents":0}

# Empty / no match
assert customer_totals([], "north") == {"customer_id":"north","order_count":0,"net_cents":0}
assert customer_totals([{"customer_id":"x","state":"settled","gross_cents":5,"refund_cents":1}], "north") == {"customer_id":"north","order_count":0,"net_cents":0}

# extra fields present; no mutation
rows = [{"order_id":"o1","customer_id":"north","state":"settled","gross_cents":1000,"refund_cents":0,"note":"z"}]
import copy
before = copy.deepcopy(rows)
customer_totals(rows, "north")
assert rows == before, "mutated input"

# no imports / no forbidden constructs in source
src = open("/workspace/customer_totals.py").read()
for bad in ["import ", "class ", "@", "global ", "eval(", "exec(", "open("]:
    assert bad not in src, bad
print("ALL TESTS PASSED")
