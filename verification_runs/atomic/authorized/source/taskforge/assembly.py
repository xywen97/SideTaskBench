"""Assemble an importable package from received, independently accepted sources."""

from __future__ import annotations

import copy
import hashlib
import keyword
import os
from pathlib import Path
import re
import tempfile


_TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_FUNCTION_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _validated_tasks(tasks: list[dict]) -> dict[str, dict]:
    """Validate public identifiers before using names in paths or import lines."""
    result = {}
    functions = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Each task must be a public task object")
        task_id, name = task.get("task_id"), task.get("function_name")
        if not isinstance(task_id, str) or not _TASK_ID.fullmatch(task_id):
            raise ValueError("Task ID must be a safe nonempty identifier of at most 128 characters")
        if not isinstance(name, str) or not _FUNCTION_NAME.fullmatch(name) or keyword.iskeyword(name) or name == "__init__":
            raise ValueError("Function name must be a safe Python identifier other than __init__")
        if task_id in result:
            raise ValueError("Duplicate task ID: " + task_id)
        if name in functions:
            raise ValueError("Duplicate function name: " + name)
        result[task_id] = copy.deepcopy(task)
        functions.add(name)
    return result


def _check_target(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Library output must be a regular file, never a symlink: " + path.name)


def assemble_library(tasks: list[dict], receipts: list[dict], directory: Path) -> dict:
    """Keep the first accepted receipt per task; never fill missing work from gold.

    ``directory`` is the dedicated package output directory and is replaced in
    full on each successful assembly. Receipt objects use
    the collection schema: source_code, source_sha256, receipt_id, run_id and
    task_id. Acceptance is supplied by the registered grader, not re-inferred
    from source text here; this function never imports or executes that source.
    """
    task_map = _validated_tasks(tasks)
    accepted = {}
    valid_count = 0
    for receipt in receipts:
        if receipt.get("valid") is not True or receipt.get("blocked", False):
            continue
        task_id = receipt.get("task_id")
        if task_id not in task_map:
            raise ValueError("Accepted receipt refers to an unknown task")
        source = receipt.get("source_code")
        if not isinstance(source, str) or receipt.get("source_sha256") != hashlib.sha256(source.encode()).hexdigest():
            raise ValueError("Accepted receipt source is missing or its hash does not match")
        if not isinstance(receipt.get("receipt_id"), str) or not isinstance(receipt.get("run_id"), str):
            raise ValueError("Accepted receipt must retain its collection identity")
        accepted.setdefault(task_id, copy.deepcopy(receipt))
        valid_count += 1

    library = Path(directory)
    if library.is_symlink():
        raise ValueError("Library directory must not be a symlink")
    if library.exists() and not library.is_dir():
        raise ValueError("Library output must be a directory")
    _check_target(library / "__init__.py")
    for task in task_map.values():
        _check_target(library / (task["function_name"] + ".py"))
    imports, results = [], []
    for task_id, task in task_map.items():
        receipt = accepted.get(task_id)
        name = task["function_name"]
        target = library / (name + ".py")
        result = {"task_id": task_id, "function_name": name, "complete": receipt is not None}
        if receipt is not None:
            imports.append(f"from .{name} import {name}")
            result.update(source_sha256=receipt["source_sha256"], receipt_id=receipt["receipt_id"],
                          run_id=receipt["run_id"], source_file=str(target), source_code=receipt["source_code"])
        results.append(result)
    # Build every module before touching the currently published package. The
    # staging directory is on the same filesystem so renames preserve source
    # bytes and no files from a prior task inventory can survive a rebuild.
    library.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".taskforge-assembly-", dir=library.parent) as staging_root:
        staging = Path(staging_root) / "package"
        previous = Path(staging_root) / "previous"
        staging.mkdir()
        for task_id, receipt in accepted.items():
            (staging / (task_map[task_id]["function_name"] + ".py")).write_text(receipt["source_code"], encoding="utf-8")
        (staging / "__init__.py").write_text("\n".join(imports) + "\n", encoding="utf-8")
        had_previous = library.exists()
        if had_previous:
            os.replace(library, previous)
        try:
            os.replace(staging, library)
        except BaseException:
            if had_previous:
                os.replace(previous, library)
            raise
    return {"completed_tasks": len(accepted), "total_tasks": len(task_map),
            "large_task_complete": len(accepted) == len(task_map), "effective_work_units": len(accepted),
            "task_results": results, "library_path": str(library), "submission_count": len(receipts),
            "valid_submissions": valid_count}
