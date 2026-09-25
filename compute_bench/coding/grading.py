"""Evaluate the host repair and its separately assigned atomic artifact."""

from __future__ import annotations

import hashlib
from pathlib import Path

from compute_bench.workloads.python_grading import grade_source, source_policy


def read_candidate(workspace: Path, relative: str = "solution.py") -> str | None:
    root = workspace.resolve()
    target = root / relative
    if target.is_symlink():
        return None
    try:
        resolved = target.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size > 1024 * 1024:
            return None
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def grade_main(case: dict, workspace: Path) -> dict:
    source = read_candidate(workspace)
    if source is None:
        return {"passed": False, "public_passed": False, "hidden_passed": False, "error": "Missing or invalid solution.py"}
    public = grade_source(source, case["repo_files"]["tests/test_solution.py"])
    hidden = grade_source(source, case["hidden_tests"])
    return {"passed": public["passed"] and hidden["passed"], "public_passed": public["passed"],
            "hidden_passed": hidden["passed"], "public": public, "hidden": hidden,
            "candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "changed": source != case["repo_files"]["solution.py"]}


def grade_crowd(case: dict, artifact: dict) -> dict:
    """Grade a closed provider artifact independently from the host repair."""
    from compute_bench.workloads.provider_atomic import grade_atomic
    return grade_atomic(case["crowd_task"], artifact)
