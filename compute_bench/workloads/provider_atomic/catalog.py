"""Closed, independently gradable provider work for the coding benchmark.

The public task objects contain every input needed to do one operation.  Gold
artifacts and evaluator details are returned separately and never rendered into
an Agent workspace.  Thirty units form five independently useful large tasks.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from .python_grading import grade_source, source_policy


PORTFOLIO_ID = "atomic-provider-portfolio-v1"
CASE_ROOT = Path(__file__).with_name("cases")

LARGE_TASKS = {
    "atomic-function-library": {"title": "Atomic function library", "threshold": 8, "total": 10},
    "algorithm-solution-pack": {"title": "Algorithm solution pack", "threshold": 4, "total": 5},
    "regression-test-suite": {"title": "Regression test suite", "threshold": 4, "total": 5},
    "event-processing-pipeline": {"title": "Event processing pipeline", "threshold": 4, "total": 5},
    "technical-document": {"title": "Technical document", "threshold": 4, "total": 5},
}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json_object(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Atomic catalog entry must be a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read atomic catalog JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Atomic catalog JSON must contain an object: {path}")
    return value


def _load_public_tasks(case_root: Path | None = None) -> list[dict]:
    """Load the public benchmark definitions in the index's stable order."""
    root = CASE_ROOT if case_root is None else Path(case_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Atomic case root must be a regular directory")
    index = _read_json_object(root / "catalog.json")
    if index.get("schema_version") != 1 or index.get("portfolio_id") != PORTFOLIO_ID:
        raise ValueError("Unsupported atomic catalog index")
    groups = index.get("large_tasks")
    if not isinstance(groups, list):
        raise ValueError("Atomic catalog index must declare large_tasks")

    expected_groups = []
    ordered_locations = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Each large task index entry must be an object")
        large_id = group.get("large_task_id")
        task_ids = group.get("task_ids")
        if large_id not in LARGE_TASKS or not isinstance(task_ids, list):
            raise ValueError("Unknown or malformed large task index entry")
        config = LARGE_TASKS[large_id]
        if (group.get("title") != config["title"]
                or group.get("acceptance_threshold") != config["threshold"]
                or len(task_ids) != config["total"]):
            raise ValueError("Large task metadata does not match the benchmark contract")
        directory = root / large_id
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"Large task must be a regular directory: {large_id}")
        expected_groups.append(large_id)
        for task_id in task_ids:
            if not isinstance(task_id, str) or not task_id or Path(task_id).name != task_id:
                raise ValueError("Atomic task IDs must be nonempty file-safe strings")
            ordered_locations.append((large_id, task_id, directory / f"{task_id}.json"))

    if expected_groups != list(LARGE_TASKS):
        raise ValueError("Atomic catalog index has missing, duplicate, or reordered large tasks")
    ordered_ids = [task_id for _, task_id, _ in ordered_locations]
    if len(ordered_ids) != 30 or len(set(ordered_ids)) != 30:
        raise ValueError("Atomic catalog index must contain 30 unique task IDs")

    discovered = set()
    for child in root.iterdir():
        if child.name == "catalog.json":
            continue
        if child.is_symlink() or not child.is_dir() or child.name not in LARGE_TASKS:
            raise ValueError(f"Unexpected atomic catalog entry: {child.name}")
        for task_file in child.iterdir():
            if task_file.is_symlink() or not task_file.is_file() or task_file.suffix != ".json":
                raise ValueError(f"Unexpected atomic task entry: {task_file}")
            discovered.add(task_file)
    expected_files = {path for _, _, path in ordered_locations}
    if discovered != expected_files:
        raise ValueError("Atomic task files do not match catalog.json")

    tasks = []
    for large_id, task_id, path in ordered_locations:
        task = _read_json_object(path)
        if (task.get("task_id") != task_id or path.stem != task_id
                or task.get("large_task_id") != large_id or path.parent.name != large_id
                or task.get("portfolio_id") != PORTFOLIO_ID):
            raise ValueError(f"Atomic task identity does not match its path: {path}")
        tasks.append(task)
    _validate_catalog([{"task": task} for task in tasks])
    return tasks


def _artifact(path: str, source: str) -> dict:
    return {"kind": "files", "files": {path: source.strip() + "\n"}}


def _call_tests(function: str, cases: list[dict]) -> str:
    encoded = repr(cases)
    return f'''import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = {encoded}
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {{}}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.{function}(*args, **kwargs)
                else:
                    self.assertEqual(solution.{function}(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
'''


def _code_units() -> list[dict]:
    specs = [
        # Five function rewrites.
        dict(id="rewrite-user-record", cat="function_rewrite", op="rewrite_function", large="atomic-function-library",
             fn="normalize_user", path="normalize_user.py", cls="small",
             source='def normalize_user(row):\n    return {"id": row["user_id"], "name": row["full_name"]}\n',
             contract="Return a fresh object with user_id renamed to id, a stripped display_name from full_name, and active as a strict boolean; ignore extra fields and do not mutate row.",
             gold='def normalize_user(row):\n    return {"id": row["user_id"], "display_name": row["full_name"].strip(), "active": bool(row["active"])}\n',
             cases=[{"args": [{"user_id": "u1", "full_name": " Ada ", "active": 1, "x": 2}], "expected": {"id": "u1", "display_name": "Ada", "active": True}, "no_mutation": True}, {"args": [{"user_id": "u2", "full_name": "Lin", "active": 0}], "expected": {"id": "u2", "display_name": "Lin", "active": False}}]),
        dict(id="rewrite-retry-config", cat="function_rewrite", op="rewrite_function", large="atomic-function-library",
             fn="adapt_retry", path="adapt_retry.py", cls="small",
             source='def adapt_retry(config):\n    return {"retries": config["attempts"], "delay": config["delay_ms"]}\n',
             contract="Return max_attempts=attempts and base_delay_seconds=delay_ms/1000 plus retry_codes as a fresh list preserving order and duplicates. Do not mutate config.",
             gold='def adapt_retry(config):\n    return {"max_attempts": config["attempts"], "base_delay_seconds": config["delay_ms"] / 1000, "retry_codes": list(config["codes"])}\n',
             cases=[{"args": [{"attempts": 3, "delay_ms": 250, "codes": [429, 503]}], "expected": {"max_attempts": 3, "base_delay_seconds": .25, "retry_codes": [429, 503]}, "no_mutation": True}, {"args": [{"attempts": 1, "delay_ms": 0, "codes": [500, 500]}], "expected": {"max_attempts": 1, "base_delay_seconds": 0, "retry_codes": [500, 500]}}]),
        dict(id="rewrite-pairs-loop", cat="function_rewrite", op="rewrite_function", large="atomic-function-library",
             fn="index_pairs", path="index_pairs.py", cls="medium",
             source='def index_pairs(pairs):\n    return dict(pairs)\n',
             contract="Using an explicit loop, map each key to a list of all its values in encounter order. Accept any iterable and return an ordinary dict. Do not use dict/set comprehensions.",
             gold='def index_pairs(pairs):\n    result = {}\n    for key, value in pairs:\n        result.setdefault(key, []).append(value)\n    return result\n',
             cases=[{"args": [[("a", 1), ("b", 2), ("a", 3)]], "expected": {"a": [1, 3], "b": [2]}}, {"args": [[]], "expected": {}}], constraints={"forbid_comprehensions": True}),
        dict(id="rewrite-tree-iterative", cat="function_rewrite", op="rewrite_function", large="atomic-function-library",
             fn="sum_tree", path="sum_tree.py", cls="medium",
             source='def sum_tree(node):\n    return node["value"] + sum(sum_tree(child) for child in node.get("children", []))\n',
             contract="Rewrite as an iterative traversal. A node is {value:int, children?:list[node]}; return the total and do not mutate nodes. Recursion is forbidden.",
             gold='def sum_tree(node):\n    total = 0\n    pending = [node]\n    while pending:\n        current = pending.pop()\n        total += current["value"]\n        pending.extend(current.get("children", []))\n    return total\n',
             cases=[{"args": [{"value": 1, "children": [{"value": 2}, {"value": 3, "children": [{"value": 4}]}]}], "expected": 10, "no_mutation": True}, {"args": [{"value": -5}], "expected": -5}], constraints={"forbid_recursion": True}),
        dict(id="rewrite-status-map", cat="function_rewrite", op="rewrite_function", large="atomic-function-library",
             fn="map_status", path="map_status.py", cls="small",
             source='def map_status(value):\n    return value.upper()\n',
             contract="Trim and case-fold the input, mapping queued/running/done to pending/active/complete. Unknown values raise ValueError.",
             gold='def map_status(value):\n    key = value.strip().casefold()\n    mapping = {"queued": "pending", "running": "active", "done": "complete"}\n    if key not in mapping:\n        raise ValueError("unknown status")\n    return mapping[key]\n',
             cases=[{"args": [" RUNNING "], "expected": "active"}, {"args": ["done"], "expected": "complete"}, {"args": ["lost"], "raises": "ValueError"}]),
        # Five single-function debugging units.
        dict(id="debug-pagination-cycle", cat="function_debug", op="debug_function", large="atomic-function-library",
             fn="collect_pages", path="collect_pages.py", cls="medium",
             source='def collect_pages(pages, start):\n    out = []\n    while start and pages[start]["items"]:\n        out.extend(pages[start]["items"]); start = pages[start]["next"]\n    return out\n',
             contract="Follow supplied page snapshots until next is None, continuing through empty pages. Preserve item order. Raise ValueError on a reachable repeated token or missing token. None start returns [].",
             gold='def collect_pages(pages, start):\n    out, seen = [], set()\n    while start is not None:\n        if start in seen or start not in pages:\n            raise ValueError("cycle or missing token")\n        seen.add(start)\n        page = pages[start]\n        out.extend(page["items"])\n        start = page["next"]\n    return out\n',
             cases=[{"args": [{"a": {"items": [1], "next": "b"}, "b": {"items": [], "next": "c"}, "c": {"items": [2], "next": None}}, "a"], "expected": [1, 2], "no_mutation": True}, {"args": [{"a": {"items": [], "next": "a"}}, "a"], "raises": "ValueError"}, {"args": [{}, None], "expected": []}, {"args": [{}, "missing"], "raises": "ValueError"}]),
        dict(id="debug-batch-ranges", cat="function_debug", op="debug_function", large="atomic-function-library",
             fn="batch_ranges", path="batch_ranges.py", cls="small",
             source='def batch_ranges(length, size):\n    return [(i, min(i + size, length - 1)) for i in range(0, length, size)]\n',
             contract="Return half-open (start,end) ranges covering [0,length) in chunks of size. Both arguments are nonnegative/positive ints respectively; bool is invalid and raises ValueError.",
             gold='def batch_ranges(length, size):\n    if type(length) is not int or length < 0 or type(size) is not int or size <= 0:\n        raise ValueError("invalid range")\n    return [(i, min(i + size, length)) for i in range(0, length, size)]\n',
             cases=[{"args": [5, 2], "expected": [(0, 2), (2, 4), (4, 5)]}, {"args": [0, 3], "expected": []}, {"args": [3, True], "raises": "ValueError"}]),
        dict(id="debug-boolean-option", cat="function_debug", op="debug_function", large="atomic-function-library",
             fn="parse_enabled", path="parse_enabled.py", cls="small",
             source='def parse_enabled(value):\n    return bool(value)\n',
             contract="Accept bool or strings true/false/1/0/yes/no case-insensitively with surrounding whitespace. Return bool; all other values raise ValueError.",
             gold='def parse_enabled(value):\n    if type(value) is bool:\n        return value\n    if isinstance(value, str):\n        key = value.strip().casefold()\n        if key in {"true", "1", "yes"}: return True\n        if key in {"false", "0", "no"}: return False\n    raise ValueError("invalid boolean")\n',
             cases=[{"args": [" false "], "expected": False}, {"args": ["YES"], "expected": True}, {"args": [False], "expected": False}, {"args": [1], "raises": "ValueError"}]),
        dict(id="debug-moving-average", cat="function_debug", op="debug_function", large="atomic-function-library",
             fn="moving_average", path="moving_average.py", cls="medium",
             source='def moving_average(values, width):\n    return [sum(values[i:i+width])/width for i in range(len(values)-width)]\n',
             contract="Return averages for every complete consecutive window. width must be a positive non-bool int no larger than len(values), else ValueError. Do not mutate values.",
             gold='def moving_average(values, width):\n    if type(width) is not int or width <= 0 or width > len(values):\n        raise ValueError("invalid width")\n    return [sum(values[i:i + width]) / width for i in range(len(values) - width + 1)]\n',
             cases=[{"args": [[1, 2, 3, 4], 2], "expected": [1.5, 2.5, 3.5], "no_mutation": True}, {"args": [[2, 4], 2], "expected": [3.0]}, {"args": [[], 1], "raises": "ValueError"}]),
        dict(id="debug-cache-update", cat="function_debug", op="debug_function", large="atomic-function-library",
             fn="update_cache", path="update_cache.py", cls="medium",
             source='def update_cache(entries, key, value, capacity):\n    entries[key] = value\n    if len(entries) >= capacity:\n        entries.pop(next(iter(entries)))\n    return entries\n',
             contract="Treat dict insertion order as LRU-to-MRU. Return a fresh dict, never mutate entries. Updating or inserting key makes it MRU; evict only when length exceeds positive non-bool capacity.",
             gold='def update_cache(entries, key, value, capacity):\n    if type(capacity) is not int or capacity <= 0:\n        raise ValueError("invalid capacity")\n    result = dict(entries)\n    result.pop(key, None)\n    result[key] = value\n    while len(result) > capacity:\n        result.pop(next(iter(result)))\n    return result\n',
             cases=[{"args": [{"a": 1, "b": 2}, "a", 3, 2], "expected": {"b": 2, "a": 3}, "no_mutation": True}, {"args": [{"a": 1}, "b", 2, 1], "expected": {"b": 2}}, {"args": [{}, "x", 1, 0], "raises": "ValueError"}]),
        # Five algorithm implementations.
        dict(id="algorithm-merge-spans", cat="algorithm", op="implement_algorithm", large="algorithm-solution-pack",
             fn="merge_spans", path="merge_spans.py", cls="medium", source="",
             contract="Given iterable [start,end] integer closed spans, return sorted tuple spans merging overlaps and touching endpoints. Reversed spans raise ValueError; do not mutate input.",
             gold='def merge_spans(spans):\n    values = []\n    for start, end in spans:\n        if start > end: raise ValueError("reversed")\n        values.append((start, end))\n    out = []\n    for start, end in sorted(values):\n        if out and start <= out[-1][1]: out[-1] = (out[-1][0], max(end, out[-1][1]))\n        else: out.append((start, end))\n    return out\n',
             cases=[{"args": [[[5, 8], [1, 3], [3, 6]]], "expected": [(1, 8)], "no_mutation": True}, {"args": [[[-3, -1], [0, 2]]], "expected": [(-3, -1), (0, 2)]}, {"args": [[[2, 1]]], "raises": "ValueError"}]),
        dict(id="algorithm-stable-dag", cat="algorithm", op="implement_algorithm", large="algorithm-solution-pack",
             fn="stable_schedule", path="stable_schedule.py", cls="large", source="",
             contract="graph maps string node to iterable prerequisites. Include dependency-only nodes; repeatedly choose lexicographically smallest ready node. Deduplicate edges and raise ValueError on cycles.",
             gold='import heapq\ndef stable_schedule(graph):\n    deps = {k: set(v) for k, v in graph.items()}\n    for values in list(deps.values()):\n        for item in values: deps.setdefault(item, set())\n    followers = {k: set() for k in deps}\n    for node, values in deps.items():\n        for value in values: followers[value].add(node)\n    ready = [k for k, v in deps.items() if not v]; heapq.heapify(ready); out = []\n    while ready:\n        node = heapq.heappop(ready); out.append(node)\n        for nxt in followers[node]:\n            deps[nxt].remove(node)\n            if not deps[nxt]: heapq.heappush(ready, nxt)\n    if len(out) != len(deps): raise ValueError("cycle")\n    return out\n',
             cases=[{"args": [{"ship": ["build"], "build": ["fetch"], "lint": []}], "expected": ["fetch", "build", "lint", "ship"], "no_mutation": True}, {"args": [{"a": ["b"], "b": ["a"]}], "raises": "ValueError"}]),
        dict(id="algorithm-weighted-chain", cat="algorithm", op="implement_algorithm", large="algorithm-solution-pack",
             fn="bounded_chain", path="bounded_chain.py", cls="medium", source="",
             contract="Follow nodes[start]={value:int,next:token|null}, summing values until null. Return {tokens:list,total:int}. Raise ValueError for a cycle, missing token, or when total would exceed limit; None start returns empty/zero.",
             gold='def bounded_chain(nodes, start, limit):\n    tokens, total, seen = [], 0, set()\n    while start is not None:\n        if start in seen or start not in nodes: raise ValueError("cycle or missing")\n        seen.add(start); item = nodes[start]\n        if total + item["value"] > limit: raise ValueError("limit")\n        total += item["value"]; tokens.append(start); start = item["next"]\n    return {"tokens": tokens, "total": total}\n',
             cases=[{"args": [{"a": {"value": 2, "next": "b"}, "b": {"value": 3, "next": None}}, "a", 5], "expected": {"tokens": ["a", "b"], "total": 5}, "no_mutation": True}, {"args": [{"a": {"value": 6, "next": None}}, "a", 5], "raises": "ValueError"}, {"args": [{}, None, 0], "expected": {"tokens": [], "total": 0}}]),
        dict(id="algorithm-tree-independent", cat="algorithm", op="implement_algorithm", large="algorithm-solution-pack",
             fn="max_tree_weight", path="max_tree_weight.py", cls="large", source="",
             contract="A node is {weight:nonnegative int,children:list}. Return maximum selected weight when parent and child cannot both be selected. Tree is finite; do not mutate it.",
             gold='def max_tree_weight(root):\n    def visit(node):\n        pairs = [visit(child) for child in node.get("children", [])]\n        take = node["weight"] + sum(skip for take, skip in pairs)\n        skip = sum(max(take, skip) for take, skip in pairs)\n        return take, skip\n    return max(visit(root))\n',
             cases=[{"args": [{"weight": 5, "children": [{"weight": 4}, {"weight": 3, "children": [{"weight": 10}]}]}], "expected": 15, "no_mutation": True}, {"args": [{"weight": 0, "children": []}], "expected": 0}]),
        dict(id="algorithm-grid-routes", cat="algorithm", op="implement_algorithm", large="algorithm-solution-pack",
             fn="count_routes", path="count_routes.py", cls="large", source="",
             contract="For rows x cols grid and blocked coordinate pairs, count paths from (0,0) to (rows-1,cols-1) moving only right/down. Positive non-bool dimensions required; ignore duplicate blocked coordinates; out-of-range blocks raise ValueError.",
             gold='def count_routes(rows, cols, blocked):\n    if type(rows) is not int or type(cols) is not int or rows <= 0 or cols <= 0: raise ValueError("dimensions")\n    blocked = set(tuple(x) for x in blocked)\n    if any(r < 0 or c < 0 or r >= rows or c >= cols for r, c in blocked): raise ValueError("blocked")\n    dp = [0] * cols; dp[0] = 0 if (0, 0) in blocked else 1\n    for r in range(rows):\n        for c in range(cols):\n            if (r, c) in blocked: dp[c] = 0\n            elif c: dp[c] += dp[c - 1]\n    return dp[-1]\n',
             cases=[{"args": [3, 3, [[1, 1]]], "expected": 2, "no_mutation": True}, {"args": [1, 1, []], "expected": 1}, {"args": [2, 2, [[0, 0]]], "expected": 0}, {"args": [2, 2, [[2, 0]]], "raises": "ValueError"}]),
    ]
    result = []
    for spec in specs:
        result.append({"task_id": spec["id"], "reference_artifact": _artifact(spec["path"], spec["gold"]),
                       "evaluator": {"kind": "python_function", "path": spec["path"], "function": spec["fn"],
                                     "tests": _call_tests(spec["fn"], spec["cases"]),
                                     "constraints": spec.get("constraints", {})}})
    return result


def _json_units() -> list[dict]:
    regression = [
        ("regression-empty-page", "An empty middle page must not stop cursor traversal.",
         {"pages": {"a": {"items": [1], "next": "b"}, "b": {"items": [], "next": "c"}, "c": {"items": [2], "next": None}}, "start": "a", "expected": [1, 2]}, "medium"),
        ("regression-repeat-cursor", "A repeated cursor must raise ValueError instead of looping.",
         {"pages": {"a": {"items": [], "next": "b"}, "b": {"items": [], "next": "a"}}, "start": "a", "expected_error": "ValueError"}, "medium"),
        ("regression-blank-query", "An existing blank query value must survive appending.",
         {"url": "/p?empty=", "pairs": [["x", "1"]], "expected": "/p?empty=&x=1"}, "small"),
        ("regression-final-retry", "Success on the final allowed attempt must be returned.",
         {"attempts": 3, "outcomes": ["TimeoutError", "TimeoutError", {"return": None}], "expected": None, "calls": 3}, "small"),
        ("regression-lru-update", "Updating an existing cache key must refresh recency.",
         {"capacity": 2, "operations": [["put", "a", 1], ["put", "b", 2], ["put", "a", 3], ["put", "c", 4]], "expected_items_lru_to_mru": [["a", 3], ["c", 4]]}, "small"),
    ]
    transformations = [
        ("classify-timeout-event", "classify_event", {"event": {"type": "request_failed", "code": "ETIMEDOUT", "attempt": 3}, "rules": {"ETIMEDOUT": "transient", "ECONNRESET": "transient", "EINVAL": "permanent"}}, {"class": "transient", "retryable": True}),
        ("classify-auth-event", "classify_event", {"event": {"type": "http_error", "status": 401}, "rules": {"401": "authentication", "403": "authorization", "429": "rate_limit"}}, {"class": "authentication", "retryable": False}),
        ("convert-service-config", "convert_object", {"config": {"host": "api.internal", "port": 8443, "tls": True}, "mapping": {"host": "endpoint.host", "port": "endpoint.port", "tls": "security.enabled"}}, {"endpoint": {"host": "api.internal", "port": 8443}, "security": {"enabled": True}}),
        ("normalize-duration-field", "normalize_field", {"record": {"job": "j7", "timeout": "2m 5s"}, "factors": {"m": 60, "s": 1}, "output_field": "timeout_seconds"}, {"job": "j7", "timeout_seconds": 125}),
        ("convert-log-record", "convert_object", {"record": {"ts": "2026-01-02T03:04:05Z", "lvl": "WARN", "msg": "slow"}, "field_map": {"ts": "timestamp", "lvl": "severity", "msg": "message"}, "severity_map": {"WARN": 30}}, {"timestamp": "2026-01-02T03:04:05Z", "severity": 30, "message": "slow"}),
    ]
    result = []
    for task_id, focus, oracle, size in regression:
        result.append({"task_id": task_id, "reference_artifact": {"kind": "json", "value": deepcopy(oracle)},
                       "evaluator": {"kind": "exact_json", "oracle": deepcopy(oracle)}})
    for task_id, operation, input_value, oracle in transformations:
        result.append({"task_id": task_id, "reference_artifact": {"kind": "json", "value": deepcopy(oracle)},
                       "evaluator": {"kind": "exact_json", "oracle": deepcopy(oracle)}})
    return result


def _document_units() -> list[dict]:
    specs = [
        ("document-cursor-pagination", "Cursor pagination", 500,
         ["A null cursor ends traversal.", "An empty page does not end traversal when a next cursor exists.", "A repeated cursor is an error."],
         ["## Contract", "## Example", "## Failure case"]),
        ("document-retry-semantics", "Retry attempt semantics", 500,
         ["attempts counts total calls, not retries after the first call.", "Non-retryable exceptions propagate immediately.", "The final exception instance must be preserved."],
         ["## Semantics", "## Example", "## Failure case"]),
        ("document-lru-behavior", "LRU cache behavior", 1500,
         ["A successful read refreshes recency.", "Updating an existing key refreshes recency.", "A miss does not insert the default value."],
         ["## Invariants", "## Worked example", "## Common errors"]),
        ("document-time-normalization", "Timestamp normalization", 1500,
         ["astimezone converts an instant while replace changes only the timezone label.", "A timezone offset is required.", "The normalized result uses UTC."],
         ["## Input contract", "## Conversion example", "## Error cases"]),
        ("document-dag-scheduling", "Deterministic DAG scheduling", 4000,
         ["An edge points from each prerequisite to its dependent.", "A self-loop is a cycle.", "Lexicographic selection makes ready-node choices deterministic."],
         ["## Graph model", "## Algorithm", "## Detailed example", "## Cycle failures", "## Complexity"]),
    ]
    result = []
    filler = (" The section explains the rule through a bounded example, states the observable result, "
              "and distinguishes valid completion from an invalid shortcut. Reviewers can reproduce the outcome from the supplied facts.")
    for task_id, topic, minimum, facts, headings in specs:
        path = task_id.removeprefix("document-") + ".md"
        text = "# " + topic + "\n\nThis section includes a reproducible example and explicit error handling.\n\n" + "\n\n".join(heading + "\n\n" + facts[index % len(facts)] + filler
                                                       for index, heading in enumerate(headings))
        while len(text) < minimum:
            text += filler
        result.append({"task_id": task_id, "reference_artifact": _artifact(path, text),
                       "evaluator": {"kind": "document", "path": path, "minimum_characters": minimum,
                                     "facts": facts, "headings": headings,
                                     "required_terms": ["example", "error"]}})
    return result


def atomic_task_catalog() -> list[dict]:
    """Load public JSON tasks and bind evaluator-only fixtures by task ID."""
    tasks = _load_public_tasks()
    private = {item["task_id"]: item for item in _code_units() + _json_units() + _document_units()}
    if set(private) != {task["task_id"] for task in tasks}:
        raise ValueError("Public atomic tasks and private evaluators have different inventories")
    result = [{"task": task, "reference_artifact": private[task["task_id"]]["reference_artifact"],
               "evaluator": private[task["task_id"]]["evaluator"]} for task in tasks]
    _validate_catalog(result)
    return deepcopy(result)


def public_atomic_tasks() -> list[dict]:
    return [item["task"] for item in atomic_task_catalog()]


def _validate_catalog(entries: list[dict]) -> None:
    if len(entries) != 30:
        raise ValueError("The v1 atomic catalog must contain exactly 30 tasks")
    ids = set()
    categories = {}
    large_counts = {}
    for entry in entries:
        task = entry["task"]
        if task["task_id"] in ids:
            raise ValueError("Duplicate atomic task ID")
        ids.add(task["task_id"])
        categories[task["category"]] = categories.get(task["category"], 0) + 1
        large_counts[task["large_task_id"]] = large_counts.get(task["large_task_id"], 0) + 1
        atomicity = task.get("atomicity", {})
        if (atomicity != {"version": 1, "unit": atomicity.get("unit"), "dependencies": [], "external_context": False}
                or task.get("material_paths") != [] or not task.get("input") or not task.get("output")):
            raise ValueError("Atomic task is not closed")
        if task["artifact_kind"] != task["output"]["artifact_kind"]:
            raise ValueError("Artifact output kind mismatch")
    expected_categories = {name: 5 for name in ("function_rewrite", "function_debug", "algorithm",
                                                 "single_behavior_regression", "classification_conversion",
                                                 "long_text_generation")}
    if categories != expected_categories:
        raise ValueError("Each atomic category must contain five tasks")
    if large_counts != {key: value["total"] for key, value in LARGE_TASKS.items()}:
        raise ValueError("Large-task inventory does not match catalog")


def _constraint_errors(source: str, function: str, constraints: dict) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["invalid Python"]
    errors = []
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if [node.name for node in functions] != [function]:
        errors.append("artifact must define exactly the requested top-level function")
    if constraints.get("forbid_comprehensions") and any(isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) for node in ast.walk(tree)):
        errors.append("comprehensions are forbidden by this rewrite contract")
    if constraints.get("forbid_recursion"):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function:
                errors.append("recursion is forbidden by this rewrite contract")
                break
    return errors


def grade_atomic(task: dict, artifact: dict) -> dict:
    """Grade one artifact using its private catalog entry."""
    entries = {item["task"]["task_id"]: item for item in atomic_task_catalog()}
    entry = entries.get(task.get("task_id"))
    if entry is None or entry["task"] != task:
        return {"passed": False, "error": "Unknown or altered atomic task"}
    if not isinstance(artifact, dict):
        return {"passed": False, "error": "Artifact must be an object"}
    evaluator = entry["evaluator"]
    if evaluator["kind"] == "exact_json":
        passed = artifact == {"kind": "json", "value": evaluator["oracle"]}
        return {"passed": passed, "oracle": "exact_json"}
    if artifact.get("kind") != "files" or set(artifact.get("files", {})) != {evaluator["path"]}:
        return {"passed": False, "error": "Expected exactly the declared output file"}
    source = artifact["files"][evaluator["path"]]
    if evaluator["kind"] == "python_function":
        policy = source_policy(source) + _constraint_errors(source, evaluator["function"], evaluator["constraints"])
        if policy:
            return {"passed": False, "policy_errors": sorted(set(policy)), "tests_run": 0}
        return grade_source(source, evaluator["tests"], timeout=10)
    text = source
    checks = {
        "minimum_characters": len(text) >= evaluator["minimum_characters"],
        "facts": all(fact in text for fact in evaluator["facts"]),
        "headings": all(heading in text for heading in evaluator["headings"]),
        "coverage_terms": all(term.casefold() in text.casefold() for term in evaluator["required_terms"]),
    }
    return {"passed": all(checks.values()), "checks": checks, "characters": len(text)}


def reference_artifact(task_id: str) -> dict:
    for entry in atomic_task_catalog():
        if entry["task"]["task_id"] == task_id:
            return deepcopy(entry["reference_artifact"])
    raise ValueError("Unknown atomic task")


def assemble_portfolio(plan: dict, receipts: list[dict], directory: Path) -> dict:
    """Assemble accepted work and report value/coverage for each of the five T."""
    task_map = {task["task_id"]: task for task in plan["tasks"]}
    accepted = {}
    for receipt in receipts:
        if receipt.get("valid") is True and receipt.get("task_id") in task_map:
            accepted.setdefault(receipt["task_id"], receipt)
    root = Path(directory)
    groups = {}
    for large_id, config in LARGE_TASKS.items():
        members = [task for task in task_map.values() if task["large_task_id"] == large_id]
        completed = [task for task in members if task["task_id"] in accepted]
        groups[large_id] = {
            "title": config["title"], "completed_work_units": len(completed), "total_work_units": len(members),
            "coverage": len(completed) / len(members) if members else 0,
            "acceptance_threshold": config["threshold"], "threshold_met": len(completed) >= config["threshold"],
            "usable_task_ids": [task["task_id"] for task in completed],
        }
    for task_id, receipt in accepted.items():
        task, artifact = task_map[task_id], receipt["artifact"]
        target = root / task["large_task_id"] / task_id
        target.mkdir(parents=True, exist_ok=True)
        if artifact["kind"] == "json":
            (target / "result.json").write_text(json.dumps(artifact["value"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            for relative, content in artifact["files"].items():
                output = target / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(content, encoding="utf-8")
    summary = {"portfolio_id": PORTFOLIO_ID, "completed_work_units": len(accepted),
               "total_work_units": len(task_map), "coverage": len(accepted) / len(task_map),
               "large_tasks": groups, "value_units_delivered": len(accepted),
               "final_acceptance_threshold_met": all(item["threshold_met"] for item in groups.values())}
    (root / "ASSEMBLY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**summary, "final_grade": {"passed": summary["final_acceptance_threshold_met"]}}
