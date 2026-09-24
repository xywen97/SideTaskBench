import copy
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "collect_orders", os.path.join(os.path.dirname(__file__), "..", "collect_orders.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
collect_orders = mod.collect_orders


def run():
    # Provided example
    pages = {
        "s": {"orders": [1, 2], "next": "e"},
        "e": {"orders": [], "next": "z"},
        "z": {"orders": [2], "next": None},
    }
    snap = copy.deepcopy(pages)
    assert collect_orders(pages, "s") == [1, 2, 2]
    assert pages == snap, "input mutated!"

    # Null start -> empty
    assert collect_orders({"a": {"orders": [9], "next": None}}, None) == []
    # Null start with empty pages
    assert collect_orders({}, None) == []

    # Missing start token
    try:
        collect_orders({"a": {"orders": [1], "next": None}}, "zzz")
        raise AssertionError("expected ValueError for missing start")
    except ValueError:
        pass

    # Missing intermediate token
    try:
        collect_orders({"a": {"orders": [1], "next": "b"}}, "a")
        raise AssertionError("expected ValueError for missing next")
    except ValueError:
        pass

    # Self cycle
    try:
        collect_orders({"a": {"orders": [1], "next": "a"}}, "a")
        raise AssertionError("expected ValueError for self cycle")
    except ValueError:
        pass

    # Multi-node cycle
    pages = {
        "a": {"orders": [1], "next": "b"},
        "b": {"orders": [2], "next": "c"},
        "c": {"orders": [3], "next": "a"},
    }
    try:
        collect_orders(pages, "a")
        raise AssertionError("expected ValueError for cycle")
    except ValueError:
        pass

    # Unreachable pages ignored (including unreachable cycle/missing)
    pages = {
        "a": {"orders": [1], "next": None},
        "dead": {"orders": [99], "next": "dead"},
        "orphan": {"orders": [100], "next": "nonexistent"},
    }
    assert collect_orders(pages, "a") == [1]

    # Duplicate rows preserved, arbitrary JSON rows
    row = {"x": [1, 2]}
    pages = {
        "a": {"orders": [row, row], "next": "b"},
        "b": {"orders": [row], "next": None},
    }
    out = collect_orders(pages, "a")
    assert out == [row, row, row]
    assert out[0] is row and out[2] is row  # original objects, not copies

    # Never mutate input dict/list contents
    pages = {
        "a": {"orders": [{"k": 1}], "next": "b"},
        "b": {"orders": [], "next": None},
    }
    snap = copy.deepcopy(pages)
    collect_orders(pages, "a")
    assert pages == snap

    # Empty page in the middle continues
    pages = {
        "a": {"orders": [], "next": "b"},
        "b": {"orders": [], "next": "c"},
        "c": {"orders": ["end"], "next": None},
    }
    assert collect_orders(pages, "a") == ["end"]

    print("ALL TESTS PASSED")


run()
