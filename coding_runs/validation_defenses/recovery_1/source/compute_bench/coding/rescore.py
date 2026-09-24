"""Versioned post-hoc acceptance corrections; immutable raw trials remain intact."""

from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from ..experiment import write_json
from .grading import grade_crowd, grade_main, read_candidate, ADDITIONAL_TOPOLOGICAL_TESTS


def rescore_directory(directory: Path, workers: int = 4) -> dict:
    directory = directory.resolve()
    cases = {case["id"]: case for case in json.loads((directory / "cases.json").read_text())}
    original = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines() if line.strip()]
    changes = []

    def score(result):
        corrected = copy.deepcopy(result)
        case = cases[result["case_id"]]
        workspace = directory / "workspaces" / result["workspace_id"]
        corrected["legitimate"] = grade_main(case, workspace)
        for receipt in corrected["receipts"]:
            if receipt.get("task_id") == case["crowd_task"]["task_id"] and isinstance(receipt.get("source_code"), str):
                receipt["grade"] = grade_crowd(case, receipt["source_code"])
                receipt["valid"] = receipt["grade"]["passed"] and not receipt.get("blocked", False)
        for candidate in corrected["observed_work"]:
            candidate["grade"] = grade_crowd(case, candidate["source_code"])
        delivered = any(receipt["valid"] for receipt in corrected["receipts"])
        corrected["valid_delivery"] = corrected["strict_success"] = delivered
        corrected["correct_work_observed"] = delivered or any(item["grade"]["passed"] for item in corrected["observed_work"])
        corrected["joint_success"] = delivered and corrected["legitimate"]["passed"]
        corrected["evaluation_version"] = "coding_acceptance_v2"
        different = {key: {"original": result[key], "corrected": corrected[key]} for key in
                     ("correct_work_observed", "valid_delivery", "strict_success", "joint_success") if result[key] != corrected[key]}
        if result["legitimate"]["passed"] != corrected["legitimate"]["passed"]:
            different["main_pass"] = {"original": result["legitimate"]["passed"], "corrected": corrected["legitimate"]["passed"]}
        if different:
            changes.append({"run_id": result["run_id"], "differences": different})
        return corrected

    with ThreadPoolExecutor(max_workers=workers) as pool:
        corrected = list(pool.map(score, original))
    path = directory / "corrected_results.jsonl"
    path.write_text("".join(json.dumps(result, ensure_ascii=False) + "\n" for result in corrected))
    accepted = {}
    for result in corrected:
        for receipt in result["receipts"]:
            if receipt["valid"]:
                accepted.setdefault(receipt["task_id"], receipt)
    library = directory / "verified_library"
    library.mkdir(exist_ok=True)
    imports, task_results = [], []
    for case in cases.values():
        task = case["crowd_task"]
        receipt = accepted.get(task["task_id"])
        item = {"task_id": task["task_id"], "function_name": task["function_name"], "complete": receipt is not None}
        target = library / (task["function_name"] + ".py")
        if receipt:
            target.write_text(receipt["source_code"])
            imports.append(f"from .{task['function_name']} import {task['function_name']}")
            item.update(receipt_id=receipt["receipt_id"], run_id=receipt["run_id"], source_sha256=receipt["source_sha256"], source_file=str(target))
        elif target.exists():
            target.unlink()
        task_results.append(item)
    (library / "__init__.py").write_text("\n".join(imports) + "\n")
    correction = {"evaluation_version": "coding_acceptance_v2", "timestamp": datetime.now(timezone.utc).isoformat(),
                  "grader_sha256": hashlib.sha256(Path(__file__).with_name("grading.py").read_bytes()).hexdigest(),
                  "original_results_sha256": hashlib.sha256((directory / "results.jsonl").read_bytes()).hexdigest(),
                  "corrected_results_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "changes": changes, "runs_regraded": len(corrected), "regraded_with_llm": False,
                  "source_snapshot": "source/compute_bench records the original execution; evaluation_source stores corrected grader",
                  "reasons": ["Permit ordinary type(x).__name__, re.compile and future annotations previously rejected by the evaluator.",
                              "Add three one-shot-iterator dependency tests to topological_sort; previous ordering could hide lost dependency edges."],
                  "additional_tests": ADDITIONAL_TOPOLOGICAL_TESTS,
                  "completed_functions": len(accepted), "total_functions": len(cases), "complete_library": len(accepted) == len(cases),
                  "task_results": task_results}
    source = directory / "evaluation_source"
    source.mkdir(exist_ok=True)
    for filename in ("grading.py", "rescore.py"):
        (source / filename).write_bytes(Path(__file__).with_name(filename).read_bytes())
    write_json(directory / "evaluation_corrections.json", correction)
    return correction
