"""Canonical JSON artifacts and safe relative paths for the v2 protocol."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import PurePosixPath
import re


MAX_ARTIFACT_BYTES = 1024 * 1024


def canonical_json(value) -> bytes:
    """Return the protocol's UTF-8 encoding, refusing non-JSON Python values."""
    def visit(item):
        if item is None or type(item) in {str, bool, int}:
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                visit(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                visit(child)
            return
        raise ValueError("Artifacts must contain only finite JSON values and string object keys")

    visit(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def artifact_digest(artifact) -> str:
    return hashlib.sha256(canonical_json(artifact)).hexdigest()


def safe_relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1024
            or "\\" in value or ":" in value or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or PurePosixPath(value).is_absolute() or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("Artifact file paths must be unambiguous safe relative POSIX paths")
    return value


def validate_artifact(artifact, expected_kind: str | None = None) -> dict:
    encoded = canonical_json(artifact)
    if len(encoded) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact exceeds the 1 MiB limit")
    if not isinstance(artifact, dict) or not isinstance(artifact.get("kind"), str) or artifact.get("kind") not in {"files", "json"}:
        raise ValueError("Artifact kind must be files or json")
    kind = artifact["kind"]
    if expected_kind is not None and kind != expected_kind:
        raise ValueError("Artifact kind does not match its registered task")
    if kind == "json":
        if set(artifact) != {"kind", "value"}:
            raise ValueError("JSON artifacts require exactly kind and value")
    else:
        files = artifact.get("files")
        if set(artifact) != {"kind", "files"} or not isinstance(files, dict) or not files:
            raise ValueError("File artifacts require a nonempty files object")
        for name, content in files.items():
            safe_relative_path(name)
            if not isinstance(content, str):
                raise ValueError("Artifact file contents must be UTF-8 text")
            content.encode("utf-8")
            parts = name.split("/")
            if any("/".join(parts[:index]) in files for index in range(1, len(parts))):
                raise ValueError("Artifact file paths cannot also be parent directories")
    return copy.deepcopy(artifact)


def validated_generic_tasks(tasks: list[dict]) -> dict[str, dict]:
    result = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Each task must be a public task object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", task_id):
            raise ValueError("Task ID must be a safe nonempty identifier of at most 128 characters")
        if task_id in result:
            raise ValueError("Duplicate task ID: " + task_id)
        if not isinstance(task.get("artifact_kind"), str) or task.get("artifact_kind") not in {"files", "json"}:
            raise ValueError("Generic task artifact_kind must be files or json")
        for field in ("description", "requirements"):
            if not isinstance(task.get(field), str) or not task[field].strip():
                raise ValueError(f"Task {task_id} needs {field}")
        if type(task.get("optional", False)) is not bool:
            raise ValueError("Task optional must be a boolean")
        canonical_json(task)
        result[task_id] = copy.deepcopy(task)
    return result


def validate_artifact_receipt(receipt: dict, task: dict) -> None:
    if (type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 2
            or type(receipt.get("valid")) is not bool):
        raise ValueError("Generic receipts require schema_version 2 and a boolean verdict")
    if receipt.get("artifact_sha256") != artifact_digest(receipt.get("artifact")):
        raise ValueError("Receipt artifact hash mismatch")
    grade = receipt.get("grade")
    if not isinstance(grade, dict) or type(grade.get("passed")) is not bool:
        raise ValueError("Receipt grade must contain a boolean passed field")
    if receipt["valid"] != (grade["passed"] and not receipt.get("blocked", False)):
        raise ValueError("Receipt acceptance disagrees with its grade")
    if receipt["valid"]:
        if receipt.get("task_id") != task["task_id"]:
            raise ValueError("Accepted receipt does not match its registered task")
        validate_artifact(receipt.get("artifact"), task["artifact_kind"])
