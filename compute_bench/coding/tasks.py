"""Build a complete, explicitly selected host/atomic task matrix."""

from copy import deepcopy
import random

from compute_bench.workloads.host_tasks import load_host_tasks
from compute_bench.workloads.provider_atomic import atomic_task_catalog


DESIGN = "full_cross_v1"


def _select(items, requested, key, label):
    if requested is None:
        return items
    if (not isinstance(requested, (list, tuple)) or not requested
            or any(not isinstance(value, str) for value in requested)):
        raise ValueError(f"{label} IDs must be a nonempty list of strings")
    if len(requested) != len(set(requested)):
        raise ValueError(f"{label} IDs must be unique")
    unknown = set(requested) - {key(item) for item in items}
    if unknown:
        raise ValueError(f"Unknown {label} IDs: " + ", ".join(sorted(unknown)))
    # Catalog order makes the plan independent of CLI argument ordering.
    return [item for item in items if key(item) in requested]


def build_coding_cases(*, host_task_ids=None, atomic_task_ids=None) -> list[dict]:
    """Return every selected atomic × host pair; omitted axes select all IDs."""
    hosts = _select(load_host_tasks(), host_task_ids, lambda item: item["id"], "host task")
    units = _select(atomic_task_catalog(), atomic_task_ids,
                    lambda item: item["task"]["task_id"], "atomic task")
    cases = []
    for unit in units:
        for host in hosts:
            case = deepcopy(host)
            case.update(id=f"{host['id']}__{unit['task']['task_id']}", host_task_id=host["id"],
                        crowd_task=deepcopy(unit["task"]),
                        crowd_reference_artifact=deepcopy(unit["reference_artifact"]),
                        crowd_evaluator=deepcopy(unit["evaluator"]))
            cases.append(case)
    return cases


def cases_for_manifest(manifest: dict) -> list[dict]:
    """Reconstruct new matrices and read historical plans without rewriting them."""
    if manifest.get("pairing_design") == DESIGN:
        return build_coding_cases(host_task_ids=manifest["host_task_ids"],
                                  atomic_task_ids=manifest["atomic_task_ids"])
    if manifest.get("pairing_design") is not None:
        raise ValueError("Unknown pairing design")
    # Historical audit compatibility only; no run option exposes this scheme.
    count = manifest["case_count"]
    rotation = manifest.get("pairing_rotation", 0)
    if type(count) is not int or not 1 <= count <= 8 or type(rotation) is not int or rotation < 0:
        raise ValueError("Invalid historical pairing metadata")
    catalog = atomic_task_catalog()
    cases = load_host_tasks()[:count]
    for index, case in enumerate(cases):
        unit = catalog[([0, 5, 10, 15, 20, 25, 2, 7][index] + rotation * count) % len(catalog)]
        case.update(crowd_task=deepcopy(unit["task"]),
                    crowd_reference_artifact=deepcopy(unit["reference_artifact"]),
                    crowd_evaluator=deepcopy(unit["evaluator"]))
    return cases


def build_run_plan(cases, conditions, defenses, repeats=8, seed=20260924):
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    for label, values, allowed in (
        ("Conditions", conditions, {"clean", "length_control", "direct", "wrapped"}),
        ("Defenses", defenses, {"none", "boundary", "egress"}),
    ):
        if not values or len(values) != len(set(values)) or not set(values) <= allowed:
            raise ValueError(f"{label} must be nonempty, valid and unique")
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Pair identifiers must be nonempty and unique")
    plan = []
    for case in cases:
        for condition in conditions:
            for defense in defenses:
                for repeat in range(1, repeats + 1):
                    trial = {"run_id": f"{case['id']}__{condition}__{defense}__r{repeat}",
                             "case_id": case["id"], "condition": condition,
                             "defense": defense, "repeat": repeat}
                    if "host_task_id" in case:
                        trial.update(host_task_id=case["host_task_id"],
                                     atomic_task_id=case["crowd_task"]["task_id"])
                    plan.append(trial)
    random.Random(seed).shuffle(plan)
    for index, trial in enumerate(plan):
        trial["workspace_id"] = f"w{index:03d}"
    return plan


def extend_run_plan(previous, requested):
    """Keep existing identities/workspaces and append only new trials."""
    old = {trial["run_id"]: trial for trial in previous}
    new = {trial["run_id"]: trial for trial in requested}
    if len(old) != len(previous) or len(new) != len(requested):
        raise ValueError("Run IDs must be unique")
    if not old.keys() <= new.keys():
        raise ValueError("Existing output contains runs outside the requested selection; keep the previous selection or use a new output directory")
    for key, trial in old.items():
        if {k: v for k, v in trial.items() if k != "workspace_id"} != {k: v for k, v in new[key].items() if k != "workspace_id"}:
            raise ValueError("Existing trial identity changed: " + key)
    workspaces = {trial["workspace_id"] for trial in previous}
    if len(workspaces) != len(previous):
        raise ValueError("Existing workspace IDs must be unique")
    result = deepcopy(previous)
    index = 0
    for trial in requested:
        if trial["run_id"] in old:
            continue
        while f"w{index:03d}" in workspaces:
            index += 1
        workspace = f"w{index:03d}"
        result.append({**trial, "workspace_id": workspace})
        workspaces.add(workspace)
    return result
