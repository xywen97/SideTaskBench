"""Build a complete, explicitly selected host/atomic task matrix."""

from copy import deepcopy
import random

from compute_bench.workloads.host_tasks import load_host_tasks
from compute_bench.workloads.provider_atomic import atomic_task_catalog
from compute_bench.workloads.provider_atomic.catalog import cross_product_units

from .pairing import HOST_TAILORED_PAIRS, normalize_pairs, pairs_from_manifest


DESIGN = "full_cross_v1"
PAIRED_DESIGN = "host_tailored_pairs_v1"

# Unit order of the pre-design catalog, used only to read historical plans.
HISTORICAL_UNIT_IDS = (
    "rewrite-user-record", "rewrite-retry-config", "rewrite-pairs-loop",
    "rewrite-tree-iterative", "rewrite-status-map", "debug-pagination-cycle",
    "debug-batch-ranges", "debug-boolean-option", "debug-moving-average",
    "debug-cache-update", "algorithm-merge-spans", "algorithm-stable-dag",
    "algorithm-weighted-chain", "algorithm-tree-independent", "algorithm-grid-routes",
    "regression-empty-page", "regression-repeat-cursor", "regression-blank-query",
    "regression-final-retry", "regression-lru-update", "classify-timeout-event",
    "classify-auth-event", "convert-service-config", "normalize-duration-field",
    "convert-log-record", "document-cursor-pagination", "document-retry-semantics",
    "document-lru-behavior", "document-time-normalization", "document-dag-scheduling",
)


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


def _bind(host: dict, unit: dict) -> dict:
    """Compose one host task with one atomic unit, matching the cross-product shape."""
    case = deepcopy(host)
    case.update(id=f"{host['id']}__{unit['task']['task_id']}", host_task_id=host["id"],
                crowd_task=deepcopy(unit["task"]),
                crowd_reference_artifact=deepcopy(unit["reference_artifact"]),
                crowd_evaluator=deepcopy(unit["evaluator"]))
    return case


def build_coding_cases(*, host_task_ids=None, atomic_task_ids=None) -> list[dict]:
    """Return every selected atomic × host pair; omitted axes select all IDs.

    Paired-only units are excluded: they are authored for one specific host
    and are consumed through ``build_paired_cases`` instead.
    """
    hosts = _select(load_host_tasks(), host_task_ids, lambda item: item["id"], "host task")
    units = _select(cross_product_units(), atomic_task_ids,
                    lambda item: item["task"]["task_id"], "atomic task")
    return [_bind(host, unit) for unit in units for host in hosts]


def build_paired_cases(pairs=None) -> list[dict]:
    """Return one case per explicit (host_task_id, atomic_task_id) pair.

    Unlike the full cross product, each host appears with exactly the side task
    authored for it.  Unknown IDs fail loudly rather than being dropped.
    """
    requested = normalize_pairs(pairs)
    hosts = {item["id"]: item for item in load_host_tasks()}
    units = {item["task"]["task_id"]: item for item in atomic_task_catalog()}
    cases = []
    for host_id, task_id in requested:
        if host_id not in hosts:
            raise ValueError("Unknown host task ID: " + host_id)
        if task_id not in units:
            raise ValueError("Unknown atomic task ID: " + task_id)
        cases.append(_bind(hosts[host_id], units[task_id]))
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Explicit pairs must not repeat a host/side-task combination")
    return cases


def cases_for_manifest(manifest: dict) -> list[dict]:
    """Reconstruct new matrices and read historical plans without rewriting them."""
    if manifest.get("pairing_design") == PAIRED_DESIGN:
        return build_paired_cases(pairs_from_manifest(manifest))
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
    catalog = {entry["task"]["task_id"]: entry for entry in atomic_task_catalog()}
    cases = load_host_tasks()[:count]
    for index, case in enumerate(cases):
        # Historical plans index the original catalog by position, so the
        # rotation uses the frozen unit order rather than the live catalog.
        unit = catalog[HISTORICAL_UNIT_IDS[([0, 5, 10, 15, 20, 25, 2, 7][index] + rotation * count)
                                           % len(HISTORICAL_UNIT_IDS)]]
        case.update(crowd_task=deepcopy(unit["task"]),
                    crowd_reference_artifact=deepcopy(unit["reference_artifact"]),
                    crowd_evaluator=deepcopy(unit["evaluator"]))
    return cases


def build_run_plan(cases, conditions, defenses, repeats=8, seed=20260924):
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    for label, values, allowed in (
        ("Conditions", conditions, {"clean", "length_control", "direct", "wrapped"}),
        ("Defenses", defenses, {"none", "boundary"}),
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
