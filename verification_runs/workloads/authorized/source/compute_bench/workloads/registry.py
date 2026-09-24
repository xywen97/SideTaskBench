"""Explicit workload discovery keeps private case implementations out of agents."""

import importlib


CASE_MODULES = {
    "api-migration": "api_migration",
    "regression-tests": "regression_tests",
    "order-reconciliation": "order_reconciliation",
    "catalog-normalization": "catalog_normalization",
}


def load_case(case_id: str, seed: int = 0):
    try:
        module = CASE_MODULES[case_id]
    except KeyError:
        raise ValueError("Unknown workload: " + str(case_id)) from None
    return importlib.import_module(".cases." + module, __package__).build_case(seed=seed)
