"""Publish v2 outputs only after a caller-supplied assembler and final grader."""

import copy
import hashlib
import os
from pathlib import Path
import stat
import tempfile

from .artifacts import canonical_json, validate_artifact_receipt, validated_generic_tasks


def output_inventory(directory: Path) -> dict[str, str]:
    """Hash regular output files without accepting symlinks or special files."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Artifact output must be a real directory")
    if any(parent.is_symlink() for parent in directory.parents):
        raise ValueError("Artifact output must not traverse symlinks")
    files = {}
    for path in sorted(directory.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError("Artifact output may contain only regular files and directories")
        if stat.S_ISREG(mode):
            files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def assemble_artifacts(plan: dict, receipts: list[dict], directory: Path, assembler) -> dict:
    if not callable(assembler):
        raise ValueError("A trusted external assembler is required for generic artifacts")
    tasks = validated_generic_tasks(plan["tasks"])
    accepted = {}
    for receipt in receipts:
        if receipt.get("valid") is True:
            task_id = receipt.get("task_id")
            if task_id not in tasks:
                raise ValueError("Accepted receipt refers to an unknown task")
            validate_artifact_receipt(receipt, tasks[task_id])
            accepted.setdefault(task_id, receipt)
    destination = Path(directory)
    if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents):
        raise ValueError("Artifact output must not traverse symlinks")
    if destination.exists() and not destination.is_dir():
        raise ValueError("Artifact output must be a directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".taskforge-artifacts-", dir=destination.parent) as staging_root:
        staging, previous = Path(staging_root) / "output", Path(staging_root) / "previous"
        staging.mkdir()
        result = assembler(copy.deepcopy(plan), copy.deepcopy(receipts), staging)
        if not isinstance(result, dict) or not isinstance(result.get("final_grade"), dict):
            raise ValueError("Assembler must return an object containing final_grade")
        if type(result["final_grade"].get("passed")) is not bool:
            raise ValueError("Final grade passed must be a boolean")
        result = copy.deepcopy(result)
        canonical_json(result)
        inventory = output_inventory(staging)
        result.update(schema_version=2, large_task_complete=result["final_grade"]["passed"],
                      completed_tasks=len(accepted), total_tasks=len(tasks), effective_work_units=len(accepted),
                      submission_count=len(receipts), valid_submissions=sum(item.get("valid") is True for item in receipts),
                      output_directory=str(destination), output_sha256=inventory,
                      task_results=[{"task_id": task_id, "optional": task.get("optional", False),
                                     "complete": task_id in accepted,
                                     **({"receipt_id": accepted[task_id]["receipt_id"],
                                         "artifact_sha256": accepted[task_id]["artifact_sha256"]} if task_id in accepted else {})}
                                    for task_id, task in tasks.items()])
        had_previous = destination.exists()
        if had_previous:
            # Refuse an already poisoned destination before replacing it.
            output_inventory(destination)
            os.replace(destination, previous)
        try:
            os.replace(staging, destination)
        except BaseException:
            if had_previous:
                os.replace(previous, destination)
            raise
    return result
