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
    solution_file = case["solution_file"]
    source = read_candidate(workspace, solution_file)
    if source is None:
        return {"passed": False, "public_passed": False, "hidden_passed": False,
                "error": f"Missing or invalid {solution_file}"}
    auxiliary = {path: read_candidate(workspace, path) or content
                 for path, content in case["repo_files"].items()
                 if path.endswith(".py") and path != solution_file}
    public = grade_source(source, case["repo_files"]["tests/test_solution.py"],
                          solution_path=solution_file, auxiliary=auxiliary)
    hidden = grade_source(source, case["hidden_tests"],
                          solution_path=solution_file, auxiliary=auxiliary)
    return {"passed": public["passed"] and hidden["passed"], "public_passed": public["passed"],
            "hidden_passed": hidden["passed"], "public": public, "hidden": hidden,
            "candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "changed": source != case["repo_files"][solution_file]}


def grade_crowd(case: dict, artifact: dict) -> dict:
    """Grade a closed provider artifact independently from the host repair."""
    from compute_bench.workloads.provider_atomic import grade_atomic
    return grade_atomic(case["crowd_task"], artifact)
