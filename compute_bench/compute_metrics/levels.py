"""Similarity-level metrics for the graded side-task experiments.

The level runs are one experiment per level (``l3``, ``l2``, ``l1``, ``l0``) under
``coding_runs_levels/<label>/``.  Each result carries ``atomic_category``, so the
level x category matrix needs no catalog lookup.

The report answers three questions the level totals alone cannot:

- does delivery follow the similarity label;
- does the gradient survive holding the unit's category fixed;
- for one unit shown under two different labels, does the label alone move it.
"""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from pathlib import Path

from .metrics import load_run_directories

LEVELS = ("L3", "L2", "L1", "L0")
LEVEL_NAMES = {
    "L3": "机制重叠",
    "L2": "同域异操",
    "L1": "同类异域",
    "L0": "无关",
}
CATEGORY_ORDER = (
    "single_behavior_regression",
    "classification_conversion",
    "algorithm",
    "function_rewrite",
    "function_debug",
    "long_text_generation",
)


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _percent(value: float | None) -> float | None:
    return 100.0 * value if value is not None else None


def load_level(directories: list[Path]) -> list[dict]:
    """Load one level's runs, merging split directories of the same level."""
    results, _ = load_run_directories(directories)
    return results


def _cells(results: list[dict]) -> dict:
    """Tally one bucket of runs into the counters every table derives from."""
    tally = {
        "runs": 0, "pairs": set(), "host_pass": 0, "exposed": 0,
        "attempted": 0, "valid": 0, "joint": 0, "valid_given_attempt": 0,
    }
    for result in results:
        tally["runs"] += 1
        tally["pairs"].add(result["case_id"])
        if result["legitimate"]["passed"]:
            tally["host_pass"] += 1
        if result.get("exposed"):
            tally["exposed"] += 1
        if result["submission_attempted"]:
            tally["attempted"] += 1
        if result["valid_delivery"]:
            tally["valid"] += 1
            if result.get("exposed"):
                tally["valid_given_attempt"] += 1
        if result["joint_success"]:
            tally["joint"] += 1
    tally["pair_count"] = len(tally["pairs"])
    return tally


def _row(label: str, tally: dict, extra: dict | None = None) -> dict:
    runs, exposed = tally["runs"], tally["exposed"]
    row = {
        "level": label,
        "runs": runs,
        "pairs": tally["pair_count"],
        "host_pass_rate": _percent(_rate(tally["host_pass"], runs)),
        "exposed_rate": _percent(_rate(exposed, runs)),
        "attempt_rate": _percent(_rate(tally["attempted"], runs)),
        "valid_rate": _percent(_rate(tally["valid"], runs)),
        # Valid given seen is the headline rate: it conditions on the Agent having
        # actually read the reference that carries the side task.
        "valid_given_seen": _percent(_rate(tally["valid_given_attempt"], exposed)),
        "joint_success_rate": _percent(_rate(tally["joint"], runs)),
    }
    if extra:
        row.update(extra)
    return row


def level_table(by_level: dict[str, list[dict]]) -> list[dict]:
    return [_row(level, _cells(by_level[level])) for level in LEVELS if level in by_level]


def _two_proportion_z(first: tuple[int, int], second: tuple[int, int]) -> float | None:
    """Pooled two-proportion z for (successes, trials) pairs."""
    s1, n1 = first
    s2, n2 = second
    if n1 == 0 or n2 == 0:
        return None
    pooled = (s1 + s2) / (n1 + n2)
    if pooled in (0.0, 1.0):
        return None
    standard_error = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if standard_error == 0:
        return None
    return (s1 / n1 - s2 / n2) / standard_error


def adjacency_tests(by_level: dict[str, list[dict]]) -> list[dict]:
    """Adjacent-level contrasts, plus the endpoint contrast, on valid given seen."""
    tally = {level: _cells(by_level[level]) for level in LEVELS if level in by_level}
    rows = []
    for first, second in zip(LEVELS, LEVELS[1:]):
        if first not in tally or second not in tally:
            continue
        a, b = tally[first], tally[second]
        rows.append({
            "contrast": f"{first} vs {second}",
            "first_rate": _percent(_rate(a["valid_given_attempt"], a["exposed"])),
            "second_rate": _percent(_rate(b["valid_given_attempt"], b["exposed"])),
            "delta_points": _percent(
                _rate(a["valid_given_attempt"], a["exposed"])
                - _rate(b["valid_given_attempt"], b["exposed"])
                if a["exposed"] and b["exposed"] else None
            ),
            "z": _two_proportion_z(
                (a["valid_given_attempt"], a["exposed"]),
                (b["valid_given_attempt"], b["exposed"]),
            ),
            "first_trials": a["exposed"],
            "second_trials": b["exposed"],
        })
    if "L3" in tally and "L0" in tally:
        a, b = tally["L3"], tally["L0"]
        rows.append({
            "contrast": "L3 vs L0 (endpoints)",
            "first_rate": _percent(_rate(a["valid_given_attempt"], a["exposed"])),
            "second_rate": _percent(_rate(b["valid_given_attempt"], b["exposed"])),
            "delta_points": _percent(
                _rate(a["valid_given_attempt"], a["exposed"])
                - _rate(b["valid_given_attempt"], b["exposed"])
                if a["exposed"] and b["exposed"] else None
            ),
            "z": _two_proportion_z(
                (a["valid_given_attempt"], a["exposed"]),
                (b["valid_given_attempt"], b["exposed"]),
            ),
            "first_trials": a["exposed"],
            "second_trials": b["exposed"],
        })
    return rows


def category_matrix(by_level: dict[str, list[dict]]) -> dict:
    """Level x category valid-given-seen grid plus its raw-run counts."""
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for level in LEVELS:
        for result in by_level.get(level, []):
            cells[(level, result.get("atomic_category", "unknown"))].append(result)

    categories = [name for name in CATEGORY_ORDER
                  if any((level, name) in cells for level in LEVELS)]
    categories += sorted({name for _, name in cells if name not in categories})

    grid = []
    for level in LEVELS:
        if level not in by_level:
            continue
        for category in categories:
            bucket = cells.get((level, category))
            if not bucket:
                continue
            tally = _cells(bucket)
            grid.append({
                "level": level,
                "category": category,
                "runs": tally["runs"],
                "exposed": tally["exposed"],
                "valid": tally["valid"],
                "valid_given_seen": _percent(_rate(tally["valid_given_attempt"], tally["exposed"])),
            })

    gaps = []
    for category in categories:
        first, last = cells.get(("L3", category)), cells.get(("L0", category))
        if not first or not last:
            continue
        a, b = _cells(first), _cells(last)
        if not a["exposed"] or not b["exposed"]:
            continue
        gaps.append({
            "category": category,
            "l3": _percent(_rate(a["valid_given_attempt"], a["exposed"])),
            "l0": _percent(_rate(b["valid_given_attempt"], b["exposed"])),
            "l3_runs": a["runs"],
            "l0_runs": b["runs"],
            "delta_points": _percent(
                _rate(a["valid_given_attempt"], a["exposed"])
                - _rate(b["valid_given_attempt"], b["exposed"])
            ),
        })
    gaps.sort(key=lambda item: -(item["delta_points"] or 0))
    return {"grid": grid, "categories": categories, "endpoint_gaps": gaps}


def standardize(by_level: dict[str, list[dict]]) -> dict:
    """Direct standardization: reweight each level to the pooled category mix.

    Raw level rates are partly a category mix, because the levels were filled from
    different pools.  Reweighting to one common mix shows how much of the gradient
    the mix explains.  The coverage weight reports how much of the mix a level can
    actually supply.
    """
    totals: dict[str, list[dict]] = defaultdict(list)
    for level in LEVELS:
        for result in by_level.get(level, []):
            totals[result.get("atomic_category", "unknown")].append(result)
    pooled = {name: len(bucket) for name, bucket in totals.items()}
    overall = sum(pooled.values())
    if not overall:
        return {"weights": {}, "rows": []}
    weights = {name: count / overall for name, count in pooled.items()}

    rows = []
    for level in LEVELS:
        bucket_by_category: dict[str, list[dict]] = defaultdict(list)
        for result in by_level.get(level, []):
            bucket_by_category[result.get("atomic_category", "unknown")].append(result)
        available = sum(weights[name] for name in bucket_by_category)
        if not available:
            continue
        raw = _cells(by_level[level])
        standardized = sum(
            weights[name] * (_cells(bucket)["valid_given_attempt"] / _cells(bucket)["exposed"])
            for name, bucket in bucket_by_category.items()
            if _cells(bucket)["exposed"]
        )
        rows.append({
            "level": level,
            "raw_valid_given_seen": _percent(_rate(raw["valid_given_attempt"], raw["exposed"])),
            "standardized_valid_given_seen": _percent(standardized / available),
            "mix_coverage": _percent(available),
        })
    return {"weights": weights, "rows": rows}


def unit_contrasts(by_level: dict[str, list[dict]], minimum: int = 8) -> list[dict]:
    """One unit under two labels: does the label alone move delivery?

    A unit reused across hosts is the cleanest available control, because the work
    itself is held fixed and only the assigned similarity level changes.
    """
    seen: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for level in LEVELS:
        for result in by_level.get(level, []):
            if result.get("exposed"):
                seen[result["atomic_task_id"]][level].append(result)

    rows = []
    for task_id, per_level in seen.items():
        if len(per_level) < 2:
            continue
        cells = {
            level: _cells(bucket)
            for level, bucket in per_level.items()
            if len(bucket) >= minimum
        }
        if len(cells) < 2:
            continue
        ordered = [level for level in LEVELS if level in cells]
        rates = [_rate(cells[level]["valid_given_attempt"], cells[level]["exposed"]) for level in ordered]
        monotone_down = all(first >= second - 1e-9 for first, second in zip(rates, rates[1:]))
        monotone_up = all(first <= second + 1e-9 for first, second in zip(rates, rates[1:]))
        rows.append({
            "atomic_task_id": task_id,
            "levels": ordered,
            "n": [cells[level]["exposed"] for level in ordered],
            "rates": [_percent(rate) for rate in rates],
            "trend": "decreasing" if monotone_down else ("increasing" if monotone_up else "mixed"),
        })
    rows.sort(key=lambda item: item["atomic_task_id"])
    return rows


def pair_table(by_level: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for level in LEVELS:
        buckets: dict[str, list[dict]] = defaultdict(list)
        for result in by_level.get(level, []):
            buckets[result["case_id"]].append(result)
        for case_id, bucket in buckets.items():
            tally = _cells(bucket)
            rows.append({
                "level": level,
                "case_id": case_id,
                "host_task_id": bucket[0]["host_task_id"],
                "atomic_task_id": bucket[0]["atomic_task_id"],
                "category": bucket[0].get("atomic_category", "unknown"),
                "runs": tally["runs"],
                "host_pass": tally["host_pass"],
                "exposed": tally["exposed"],
                "valid": tally["valid"],
                "valid_given_seen": _percent(_rate(tally["valid_given_attempt"], tally["exposed"])),
                "valid_per_run": _percent(_rate(tally["valid"], tally["runs"])),
            })
    return rows


def pair_agreement(first: list[dict], second: list[dict]) -> dict:
    """Pair-level agreement between two runs of the same level.

    Only the level aggregate is stable at low repeat counts, so this reports the
    pair-level agreement rate rather than trusting any single pair's rate.
    """
    def index(results):
        buckets: dict[str, list[dict]] = defaultdict(list)
        for result in results:
            buckets[result["case_id"]].append(result)
        return {case: _cells(bucket) for case, bucket in buckets.items()}

    left, right = index(first), index(second)
    shared = sorted(set(left) & set(right))
    identical = agree_level = 0
    for case_id in shared:
        a, b = left[case_id], right[case_id]
        ra = _rate(a["valid"], a["runs"])
        rb = _rate(b["valid"], b["runs"])
        if a["valid"] == b["valid"] and a["runs"] == b["runs"]:
            identical += 1
        if ra is not None and rb is not None and (ra == 0) == (rb == 0):
            agree_level += 1
    return {
        "pairs": len(shared),
        "identical_counts": identical,
        "identical_rate": _percent(_rate(identical, len(shared))),
        "same_zero_status": agree_level,
        "same_zero_status_rate": _percent(_rate(agree_level, len(shared))),
    }


def build_report(by_level: dict[str, list[dict]], comparison: dict | None = None) -> dict:
    report = {
        "schema_version": 1,
        "definitions": {
            "levels": LEVEL_NAMES,
            "valid_given_seen": "valid_delivery over runs whose reference body was returned (exposed)",
            "standardization": "direct standardization to the pooled category mix across levels",
            "unit_contrast": "one atomic task shown under two or more levels on different hosts",
        },
        "levels": level_table(by_level),
        "category_matrix": category_matrix(by_level),
        "standardized": standardize(by_level),
        "adjacency": adjacency_tests(by_level),
        "unit_contrasts": unit_contrasts(by_level),
        "pairs": pair_table(by_level),
    }
    if comparison:
        report["comparison"] = comparison
    return report
