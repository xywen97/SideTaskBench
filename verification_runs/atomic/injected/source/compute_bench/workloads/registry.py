"""JSON defines workloads; a small allowlist resolves trusted Python backends."""

import copy
import importlib

from .contracts import WorkloadCase
from .definitions import available_definitions, load_definition


# These register capabilities, not task definitions. New JSON cases may reuse a
# backend; a new grading algorithm still needs a reviewed implementation here.
BACKENDS = {
    "api-migration-v1": ("api_migration", None),
    "regression-tests-v1": ("regression_tests", "regression-tests-v1"),
    "order-reconciliation-v1": ("order_reconciliation", "order-reconciliation-v1"),
    "catalog-normalization-v1": ("catalog_normalization", "catalog-normalization-v1"),
    "api-migration-atomic-v1": ("atomic_api", None),
    "regression-tests-atomic-v1": ("atomic_regression", None),
    "order-reconciliation-atomic-v1": ("atomic_reconciliation", None),
    "catalog-normalization-atomic-v1": ("atomic_catalog", None),
}


def _backend(definition):
    try:
        module, generator_id = BACKENDS[definition["evaluator_id"]]
    except KeyError:
        raise ValueError("Unregistered evaluator_id: " + str(definition["evaluator_id"])) from None
    if definition["generator_id"] != generator_id or definition["assembler_id"] != definition["evaluator_id"]:
        raise ValueError("Generator/assembler IDs do not match the registered backend")
    return module


CASE_MODULES = {case_id: _backend(definition) for case_id, definition in available_definitions().items()}


def load_case(case_id: str, seed: int = 0) -> WorkloadCase:
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    definition, materials = load_definition(case_id)
    module = _backend(definition)
    case = importlib.import_module(".evaluators." + module, __package__).build_case(
        copy.deepcopy(definition), materials.copy(), seed=seed)
    if not isinstance(case, WorkloadCase) or any(getattr(case, key) != definition[key]
                                              for key in ("case_id", "title", "objective", "tasks")):
        raise ValueError("A backend must preserve the JSON task definition")
    if set(case.public_files) != set(materials) | set(definition["generated_materials"]):
        raise ValueError("Backend output does not match the declared public material inventory")
    if any(case.public_files.get(path) != content for path, content in materials.items()):
        raise ValueError("A backend must preserve static public material contents")
    if any(not isinstance(content, str) for content in case.public_files.values()):
        raise ValueError("Public materials must be UTF-8 text")
    return case
