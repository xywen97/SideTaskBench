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
import re
import unicodedata

from ..python_grading import grade_source, source_policy
from ..resources import read_json, read_text


PORTFOLIO_ID = "atomic-provider-portfolio-v1"
CASE_ROOT = Path(__file__).with_name("cases")

PRIVATE_ROOT = Path(__file__).with_name("private")


def _read_json_object(path: Path) -> dict:
    value = read_json(path.parent, path.name)
    if not isinstance(value, dict):
        raise ValueError(f"Atomic catalog JSON must contain an object: {path}")
    return value


# Public catalog.json is the single source of large-task metadata.
LARGE_TASKS = {
    item["large_task_id"]: {
        "title": item["title"], "threshold": item["acceptance_threshold"],
        "total": len(item["task_ids"]),
    }
    for item in _read_json_object(CASE_ROOT / "catalog.json")["large_tasks"]
}


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


def _load_private(task_id: str) -> dict:
    root = PRIVATE_ROOT / task_id
    entry = _read_json_object(root / "evaluation.json")
    if entry.get("task_id") != task_id:
        raise ValueError("Private evaluator task identity mismatch")
    evaluator = entry["evaluator"]
    if evaluator.get("kind") not in {"python_function", "exact_json", "document"}:
        raise ValueError("Unknown atomic evaluator kind")
    if evaluator["kind"] == "python_function":
        evaluator["tests"] = read_text(root, evaluator.pop("tests_file"))
    reference = entry["reference"]
    if reference["kind"] == "files":
        artifact = {"kind": "files", "files": {
            path: read_text(root, source) for path, source in reference["files"].items()
        }}
    elif reference["kind"] == "json":
        artifact = {"kind": "json", "value": read_json(root, reference["path"])}
    else:
        raise ValueError("Unknown reference artifact kind")
    return {"task_id": task_id, "evaluator": evaluator, "reference_artifact": artifact}


def atomic_task_catalog() -> list[dict]:
    """Load public JSON tasks and bind evaluator-only fixtures by task ID."""
    tasks = _load_public_tasks()
    if PRIVATE_ROOT.is_symlink() or not PRIVATE_ROOT.is_dir():
        raise ValueError("Private evaluator root must be a regular directory")
    folders = list(PRIVATE_ROOT.iterdir())
    if (any(path.is_symlink() or not path.is_dir() for path in folders)
            or {path.name for path in folders} != {task["task_id"] for task in tasks}):
        raise ValueError("Private evaluator inventory must match public tasks")
    private = {task["task_id"]: _load_private(task["task_id"]) for task in tasks}
    if set(private) != {task["task_id"] for task in tasks}:
        raise ValueError("Public atomic tasks and private evaluators have different inventories")
    result = [{"task": task, "reference_artifact": private[task["task_id"]]["reference_artifact"],
               "evaluator": private[task["task_id"]]["evaluator"]} for task in tasks]
    for entry in result:
        public, evaluator = entry["task"]["input"], entry["evaluator"]
        if evaluator["kind"] == "document":
            if (evaluator["facts"] != public["facts"]
                    or evaluator["fact_paraphrases"] != public["fact_paraphrases"]
                    or len(evaluator["fact_paraphrases"]) != len(evaluator["facts"])
                    or evaluator["headings"] != public["required_headings"]
                    or evaluator["minimum_characters"] != public["minimum_characters"]):
                raise ValueError("Public document contract and evaluator disagree")
    _validate_catalog(result)
    return deepcopy(result)


def public_atomic_tasks() -> list[dict]:
    return deepcopy(_load_public_tasks())


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


def _document_words(text: str) -> str:
    """Normalize presentation, preserving word order and negation words."""
    text = unicodedata.normalize("NFKC", text).casefold()
    # Keep link labels, not destinations. Inline emphasis/code is presentation.
    text = re.sub(r"\[([^\]]+)\]\([^\n)]*\)", r"\1", text)
    text = re.sub(r"[`*_]", "", text)
    return " ".join(re.findall(r"\w+", text))


def _contains_document_phrase(text: str, phrase: str) -> bool:
    phrase = _document_words(phrase)
    return bool(phrase) and f" {phrase} " in f" {text} "


def _grade_document(text: str, evaluator: dict) -> dict:
    """Deterministic fact coverage, not a general semantic truth classifier.

    Only explicitly declared equivalents are accepted. No fuzzy similarity or
    keyword bag is used: those can erase negations or reverse edge direction.
    """
    normalized = _document_words(text)
    alternatives = evaluator["fact_paraphrases"]
    evidence = [next((phrase for phrase in [fact, *variants]
                      if _contains_document_phrase(normalized, phrase)), None)
                for fact, variants in zip(evaluator["facts"], alternatives, strict=True)]
    headings = {_document_words(match.group(1)) for match in
                re.finditer(r"(?m)^ {0,3}##[ \t]+(.+?)[ \t]*$", text)}
    checks = {
        "minimum_characters": len(text) >= evaluator["minimum_characters"],
        "facts": all(item is not None for item in evidence),
        "headings": all(_document_words(heading) in headings for heading in evaluator["headings"]),
        "coverage_terms": all(any(_contains_document_phrase(normalized, term) for term in group)
                              for group in evaluator["required_term_groups"]),
    }
    return {"passed": all(checks.values()), "checks": checks, "characters": len(text),
            "fact_matching": "normalized_declared_variants_v1", "fact_evidence": evidence,
            "unmatched_facts": [fact for fact, match in zip(evaluator["facts"], evidence) if match is None]}


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
    return _grade_document(source, evaluator)


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
