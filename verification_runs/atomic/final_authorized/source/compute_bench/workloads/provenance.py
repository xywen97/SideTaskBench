"""Versioned workload definitions and a narrowly pinned evaluator migration.

Run snapshots are data, never imported code. A legacy migration is permitted
only by the certificate shipped with this trusted package, with both ends of
the migration pinned byte-for-byte and its public specification checked again.
"""

import hashlib
import importlib.util
import json
from pathlib import Path

from .contracts import checked_relative
from .registry import CASE_MODULES


DEFINITION_VERSION = 1
RESOURCE_ROOT = "workload_resources"
LEGACY_CASE_ORDER = ("api-migration", "regression-tests", "order-reconciliation", "catalog-normalization")
MIGRATION_FILE = Path(__file__).parent / "migrations/python_cases_to_json_v1.json"
SOURCE_FIELDS = {"compute_bench": "source_sha256", "microcoder": "agent_source_sha256",
                 "taskforge": "platform_source_sha256"}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def evaluator_requirements(case_ids, *, definition_version=None) -> dict[str, set[str]]:
    modern = definition_version == DEFINITION_VERSION
    directory = "evaluators" if modern else "cases"
    required = {"compute_bench": {"workloads/contracts.py", "workloads/evaluation.py", "workloads/isolation.py",
                                 "workloads/registry.py", f"workloads/{directory}/__init__.py",
                                 "coding/tasks.py", "coding/grading.py"},
                "microcoder": {"sandbox/__init__.py", "sandbox/linux.py"},
                "taskforge": {"artifacts.py"}}
    if modern:
        required["compute_bench"].update({"workloads/definitions.py", "workloads/packets.py"})
        required["taskforge"].add("models.py")
    required["compute_bench"].update(f"workloads/{directory}/{CASE_MODULES[case_id]}.py" for case_id in case_ids)
    if "regression-tests" in case_ids:
        required["compute_bench"].add(f"workloads/{directory}/api_migration.py")
    if modern:
        modules = {CASE_MODULES[case_id] for case_id in case_ids}
        if modules & {"atomic_api", "atomic_regression"}:
            required["compute_bench"].add("workloads/evaluators/api_migration.py")
        if "atomic_regression" in modules:
            required["compute_bench"].add("workloads/evaluators/regression_tests.py")
        if modules & {"atomic_regression", "atomic_reconciliation", "atomic_catalog"}:
            required["compute_bench"].add("workloads/evaluators/atomic_common.py")
    return required


def package_root(package: str) -> Path:
    return Path(importlib.util.find_spec(package).origin).resolve().parent


def current_evaluator_hashes(case_ids, *, definition_version=DEFINITION_VERSION) -> dict:
    result = {}
    for package, names in evaluator_requirements(case_ids, definition_version=definition_version).items():
        base = package_root(package)
        result[package] = {}
        for name in sorted(names):
            path = base / name
            if not path.is_file() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
                raise ValueError("Missing or unsafe evaluator source: " + package + "/" + name)
            result[package][name] = digest(path.read_bytes())
    return result


def current_resources(case_ids) -> dict[str, bytes]:
    from .definitions import case_resources
    result = {}
    for case_id in case_ids:
        resources = case_resources(case_id)
        definitions = [name for name in resources if len(Path(name).parts) == 2 and name.endswith("/task.json")]
        if len(definitions) != 1:
            raise ValueError("Case resources must include their task.json")
        prefix = definitions[0].removesuffix("task.json")
        if json.loads(resources[definitions[0]])["case_id"] != case_id:
            raise ValueError("Case resource definition identity mismatch")
        for relative, content in resources.items():
            checked_relative(relative)
            if not relative.startswith(prefix) or not isinstance(content, bytes) or relative in result:
                raise ValueError("Invalid or duplicate workload resource")
            result[relative] = content
    return result


def current_resource_hashes(case_ids) -> dict[str, str]:
    return {name: digest(content) for name, content in sorted(current_resources(case_ids).items())}


def snapshot_resources(directory: Path) -> dict:
    root = Path(directory).absolute()
    destination = root / RESOURCE_ROOT
    if (root.is_symlink() or any(parent.is_symlink() for parent in root.parents)
            or destination.exists() or destination.is_symlink()):
        raise ValueError("Workload resource snapshot requires a fresh, safe destination")
    # Catalogue ordering selects the legitimate coding task, so unselected
    # definitions are dependencies too. Freeze the entire small catalogue.
    case_ids = list(CASE_MODULES)
    resources = current_resources(case_ids)
    hashes = {}
    for relative, content in sorted(resources.items()):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        hashes[relative] = digest(content)
    return {"workload_definition_version": DEFINITION_VERSION, "workload_resource_root": RESOURCE_ROOT,
            "workload_resource_sha256": hashes, "workload_resource_case_ids": case_ids}


def migration_certificate() -> dict | None:
    """Only this trusted package location can authorize the known migration."""
    if (not MIGRATION_FILE.is_file() or MIGRATION_FILE.is_symlink()
            or any(parent.is_symlink() for parent in MIGRATION_FILE.absolute().parents)):
        return None
    value = json.loads(MIGRATION_FILE.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or value.get("migration_id") != "python-cases-to-json-v1" or value.get("status") != "verified"
            or value.get("allowed_seeds") != [0, 7, 41, 2026]
            or set(value.get("case_ids", [])) != set(LEGACY_CASE_ORDER)):
        return None
    return value


def migration_matches(manifest: dict) -> dict | None:
    """Return the pinned certificate only after the complete dependency gate."""
    if "workload_definition_version" in manifest:
        return None
    certificate = migration_certificate()
    if certificate is None or manifest.get("seed") not in certificate["allowed_seeds"]:
        return None
    if not set(manifest["case_ids"]).issubset(certificate["case_ids"]):
        return None
    old = certificate.get("legacy_source_sha256")
    if not isinstance(old, dict) or set(old) != set(SOURCE_FIELDS):
        return None
    requirements = evaluator_requirements(certificate["case_ids"])
    for package, names in requirements.items():
        if set(old.get(package, {})) != names:
            return None
        if any(manifest.get(SOURCE_FIELDS[package], {}).get(name) != expected
               for name, expected in old[package].items()):
            return None
    if current_evaluator_hashes(certificate["case_ids"]) != certificate.get("current_source_sha256"):
        return None
    if current_resource_hashes(certificate["case_ids"]) != certificate.get("current_resource_sha256"):
        return None
    specs = certificate.get("public_spec_sha256", {})
    for case_id in manifest["case_ids"]:
        pinned = specs.get(case_id, {}).get(str(manifest["seed"]))
        if not isinstance(pinned, str) or pinned != manifest.get("public_spec_sha256", {}).get(case_id):
            return None
    return certificate
