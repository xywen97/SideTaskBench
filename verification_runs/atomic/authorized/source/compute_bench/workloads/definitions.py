"""Read declarative cases and their explicit public files without executing them."""

import copy
import json
import math
from pathlib import Path

from taskforge.models import TaskPlan, identifier
from .contracts import checked_relative
from .packets import is_closed, validate_packet


CASE_ROOT = Path(__file__).with_name("cases")
_REQUIRED = {"schema_version", "case_number", "case_id", "title", "objective", "tasks", "materials",
             "generator_id", "generated_materials", "evaluator_id", "assembler_id"}
_OPTIONAL = {"$schema", "parameters", "bindings"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON field: " + key)
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Non-finite values are not JSON: " + value)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        _nonfinite(value)
    return number


def _regular_file(path: Path) -> Path:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.absolute().parents) or not path.is_file():
        raise ValueError("Case resources must be regular files without symlinks: " + str(path))
    return path


def _validate(value: dict) -> None:
    """Enforce schema.json plus task protocol and relative-path constraints."""
    if not isinstance(value, dict) or not _REQUIRED.issubset(value) or set(value) - _REQUIRED - _OPTIONAL:
        raise ValueError("Case JSON has missing or unsupported fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported case schema_version")
    if type(value["case_number"]) is not int or value["case_number"] < 1:
        raise ValueError("case_number must be a positive integer")
    for field in ("case_id", "evaluator_id", "assembler_id"):
        identifier(value[field])
    if value["generator_id"] is not None:
        identifier(value["generator_id"])
    for field in ("title", "objective"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError("Case needs a nonempty " + field)
    if "$schema" in value and not isinstance(value["$schema"], str):
        raise ValueError("$schema must be a string")
    for field in ("bindings", "parameters"):
        if field in value and not isinstance(value[field], dict):
            raise ValueError(field + " must be a JSON object")
    if not isinstance(value["tasks"], list):
        raise ValueError("tasks must be a list")
    TaskPlan(value["case_id"], value["objective"], tuple(value["tasks"]), {}, schema_version=2)
    materials, generated = value["materials"], value["generated_materials"]
    if not isinstance(materials, dict) or not isinstance(generated, list):
        raise ValueError("Expected a material mapping and generated_materials list")
    for output, source in materials.items():
        checked_relative(output)
        checked_relative(source)
        if not source.startswith("materials/"):
            raise ValueError("Static public inputs must be inside the case materials/ directory")
    for output in generated:
        checked_relative(output)
    if len(set(generated)) != len(generated) or set(materials).intersection(generated):
        raise ValueError("Material output paths must be unique")
    if bool(generated) != (value["generator_id"] is not None):
        raise ValueError("Generated materials require a generator_id; static cases use null")
    outputs = set(materials) | set(generated)
    if not outputs and not all(is_closed(task) for task in value["tasks"]):
        raise ValueError("A case must declare its public materials")
    for output in outputs:
        if any(parent.as_posix() in outputs for parent in Path(output).parents if parent.as_posix() != "."):
            raise ValueError("A material cannot be both a file and a parent directory")
    for task in value["tasks"]:
        validate_packet(task)
        if "title" in task and not isinstance(task["title"], str):
            raise ValueError("Task title must be a string")
        paths = task.get("material_paths", [])
        if not isinstance(paths, list) or any(not isinstance(path, str) or path not in outputs for path in paths):
            raise ValueError("Task material_paths must reference declared public files")


def _read(path: Path) -> dict:
    value = json.loads(_regular_file(path).read_text(encoding="utf-8"),
                       object_pairs_hook=_unique_object, parse_constant=_nonfinite, parse_float=_finite_float)
    _validate(value)
    return value


def _catalog():
    entries = [(path, _read(path)) for path in CASE_ROOT.glob("*/task.json")]
    if not entries:
        raise ValueError("No JSON workload definitions found")
    entries.sort(key=lambda item: (item[1]["case_number"], item[1]["case_id"]))
    ids = [value["case_id"] for _, value in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Repeated case_id in workload definitions")
    return entries


def available_definitions() -> dict[str, dict]:
    return {value["case_id"]: copy.deepcopy(value) for _, value in _catalog()}


def _entry(case_id):
    for path, value in _catalog():
        if value["case_id"] == case_id:
            return path, value
    raise ValueError("Unknown workload: " + str(case_id))


def case_definition(case_id: str) -> dict:
    """Return the actual editable task.json, not a Python-generated substitute."""
    return copy.deepcopy(_entry(case_id)[1])


def load_definition(case_id: str) -> tuple[dict, dict[str, str]]:
    path, value = _entry(case_id)
    materials = {output: _regular_file(path.parent / source).read_bytes().decode("utf-8")
                 for output, source in value["materials"].items()}
    return copy.deepcopy(value), materials


def case_resources(case_id: str) -> dict[str, bytes]:
    """Exact bytes required to reproduce the case, relative to cases/."""
    path, value = _entry(case_id)
    paths = {path, *(path.parent / source for source in value["materials"].values())}
    return {item.relative_to(CASE_ROOT).as_posix(): _regular_file(item).read_bytes() for item in sorted(paths)}
