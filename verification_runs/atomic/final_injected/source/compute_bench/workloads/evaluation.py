"""Trusted assembly adapter and deterministic checks, independent of Agent runs."""

import copy
from pathlib import Path

from compute_bench.io import write_json
from .contracts import canonical_hash, write_files
from .registry import CASE_MODULES, load_case


def assemble_result(case, receipts, directory: Path) -> dict:
    artifact = case.assemble(receipts)
    final_grade = case.grade_final(artifact)
    write_json(directory / "artifact.json", artifact)
    if artifact.get("kind") == "files":
        write_files(directory / "files", artifact["files"])
    return {"artifact": artifact, "artifact_sha256": canonical_hash(artifact),
            "final_grade": final_grade}


def fixture_receipts(case, *, omit_optional=False):
    """Gold fixtures are for evaluator checks only, never for filling Agent results."""
    receipts = []
    for task in case.tasks:
        if omit_optional and task.get("optional", False):
            continue
        task_id = task["task_id"]
        artifact = copy.deepcopy(case.reference_artifacts[task_id])
        grade = case.grade_task(task_id, artifact)
        receipts.append({"schema_version": 2, "receipt_id": "fixture-" + task_id,
                         "task_id": task_id, "artifact": artifact,
                         "artifact_sha256": canonical_hash(artifact), "grade": grade,
                         "valid": grade.get("passed") is True, "blocked": False})
    return receipts


def check_cases(case_ids=None, *, seed=0) -> dict:
    results = []
    for case_id in case_ids or CASE_MODULES:
        case = load_case(case_id, seed=seed)
        receipts = fixture_receipts(case)
        core = [item for item in receipts if not case.task(item["task_id"]).get("optional", False)]
        full = case.grade_final(case.assemble(receipts))
        without_optional = case.grade_final(case.assemble(core))
        empty = case.grade_final(case.assemble([]))
        duplicate = case.grade_final(case.assemble(core + copy.deepcopy(core)))
        rejected = copy.deepcopy(receipts)
        for receipt in rejected:
            receipt.update(valid=False, grade={"passed": False})
        rejected_grade = case.grade_final(case.assemble(rejected))
        checks = {"reference_contributions_pass": all(r["valid"] for r in receipts),
                  "assembled_final_pass": full.get("passed") is True,
                  "optional_evidence_not_required": without_optional.get("passed") is True,
                  "empty_results_fail": empty.get("passed") is False,
                  "rejected_results_cannot_complete": rejected_grade.get("passed") is False,
                  "duplicate_results_still_valid": duplicate.get("passed") is True}
        results.append({"case_id": case_id, "tasks": len(case.tasks), "checks": checks,
                        "passed": all(checks.values()), "final_grade": full})
    return {"kind": "deterministic_fixture_validation", "seed": seed,
            "passed": all(item["passed"] for item in results), "cases": results}
