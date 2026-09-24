import copy, importlib.util, json

spec = importlib.util.spec_from_file_location("collect_orders", "/workspace/collect_orders.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
collect_orders = m.collect_orders


def check(name, got, expected):
    assert got == expected, "%s: got %r expected %r" % (name, got, expected)
    print("ok:", name)


# provided example
pages = {
    "s": {"orders": [1, 2], "next": "e"},
    "e": {"orders": [], "next": "z"},
    "z": {"orders": [2], "next": None},
}
check("example", collect_orders(pages, "s"), [1, 2, 2])

# null start
check("null start", collect_orders(pages, None), [])

# duplicate rows preserved (same object identity)
rows = [{"a": 1}, {"a": 1}]
p2 = {"s": {"orders": rows, "next": None}}
out = collect_orders(p2, "s")
check("dup rows value", out, [{"a": 1}, {"a": 1}])
assert out[0] is rows[0] and out[1] is rows[1], "rows should not be copied"

# unreachable pages ignored (never raise even if they are broken/missing)
p3 = {
    "s": {"orders": ["only"], "next": None},
    "bad": {"orders": ["nope"], "next": "bad"},
    "dangling": {"orders": [], "next": "ghost"},
}
check("unreachable ignored", collect_orders(p3, "s"), ["only"])

# missing reachable token
p4 = {"s": {"orders": [1], "next": "ghost"}}
try:
    collect_orders(p4, "ghost")
    raise AssertionError("expected ValueError for missing start")
except ValueError:
    print("ok: missing start")
try:
    collect_orders(p4, "s")
    raise AssertionError("expected ValueError for missing next")
except ValueError:
    print("ok: missing next")

# cycle
p5 = {"a": {"orders": [1], "next": "b"}, "b": {"orders": [2], "next": "a"}}
try:
    collect_orders(p5, "a")
    raise AssertionError("expected ValueError for cycle")
except ValueError:
    print("ok: cycle")

# self cycle
p6 = {"a": {"orders": [], "next": "a"}}
try:
    collect_orders(p6, "a")
    raise AssertionError("expected ValueError for self-cycle")
except ValueError:
    print("ok: self-cycle")

# no mutation of inputs
p7 = {"s": {"orders": [1, 2], "next": "e"}, "e": {"orders": [3], "next": None}}
snapshot = copy.deepcopy(p7)
collect_orders(p7, "s")
assert p7 == snapshot, "inputs mutated"
print("ok: no mutation")

# empty orders key default tolerated
p8 = {"s": {"next": None}}
check("missing orders key", collect_orders(p8, "s"), [])

# large chain sanity
big = {}
for i in range(1000):
    big["t%d" % i] = {"orders": [i], "next": "t%d" % (i + 1) if i < 999 else None}
check("large chain length", len(collect_orders(big, "t0")), 1000)

print("ALL TESTS PASSED")
