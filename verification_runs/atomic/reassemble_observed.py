"""Reassemble only real receipts with full acknowledgements in the original trace.

This is a derived reconstruction with current evaluators, not a replacement for
the original run or a claim that its whole-run transport audit passed.
Run from PoC: python verification_runs/atomic/reassemble_observed.py
"""

import json
from pathlib import Path

from compute_bench.io import write_json
from compute_bench.workloads.audit import _objects, _semantic_grade, audit_directory
from compute_bench.workloads.contracts import canonical_hash
from compute_bench.workloads.evaluation import assemble_result
from compute_bench.workloads.provenance import current_evaluator_hashes, current_resource_hashes
from compute_bench.workloads.registry import load_case


def main():
    base = Path(__file__).resolve().parent
    source, output = base / "authorized", base / "observed_reassembly"
    if output.exists():
        raise ValueError("Derived output must be new; never overwrite prior evidence")
    manifest = json.loads((source / "manifest.json").read_text())
    evidence = audit_directory(source)
    # Keep the original audit failure explicit. Only its known ACK omissions
    # may be absent; all source, journal, identity and artifact checks must pass.
    unexpected = [e for e in evidence["errors"] if not e.startswith(("receipt_trace_inventory/", "receipt_http_trace/"))]
    if unexpected:
        raise ValueError("Evidence integrity failed: " + repr(unexpected))
    acknowledgements = {}
    for path in sorted((source / "traces").glob("*.jsonl")):
        by_id = {}
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event.get("kind") != "tool" or event.get("name") != "shell":
                continue
            for value in _objects(event.get("result", {}).get("stdout", "")):
                if isinstance(value.get("receipt_id"), str) and {"accepted", "valid", "task_id"}.issubset(value):
                    by_id[value["receipt_id"]] = value
        acknowledgements[path.stem] = by_id
    jobs = []
    for job in manifest["jobs"]:
        case = load_case(job["case_id"], seed=manifest["seed"])
        journal = source / job["directory"] / "collector/receipts.jsonl"
        receipts = [json.loads(line) for line in journal.read_text().splitlines()]
        selected, omitted = [], []
        for receipt in receipts:
            expected_ack = {"receipt_id": receipt["receipt_id"], "accepted": True,
                            "valid": receipt["valid"], "task_id": receipt["task_id"]}
            if acknowledgements.get(receipt["run_id"], {}).get(receipt["receipt_id"]) != expected_ack:
                omitted.append(receipt["receipt_id"])
                continue
            grade = case.grade_task(receipt["task_id"], receipt["artifact"])
            if _semantic_grade(grade) != _semantic_grade(receipt["grade"]):
                raise ValueError("Receipt grade changed: " + receipt["receipt_id"])
            selected.append(receipt)
        result = assemble_result(case, selected, output / job["case_id"])
        jobs.append({"case_id": case.case_id, "original_receipts": len(receipts),
                     "acknowledged_receipts": len(selected), "selected_receipt_ids": [r["receipt_id"] for r in selected],
                     "omitted_unacknowledged_receipt_ids": omitted,
                     "completed_work_units": len({r["task_id"] for r in selected if r["valid"]}),
                     "original_receipts_sha256": canonical_hash(receipts),
                     "selected_receipts_sha256": canonical_hash(selected),
                     "artifact_sha256": result["artifact_sha256"], "final_grade": result["final_grade"]})
    report = {"kind": "derived_reassembly_of_trace_acknowledged_real_receipts", "llm_calls": 0,
              "original_whole_run_audit_passed": evidence["passed"],
              "original_audit_limit": "One Agent hid intermediate HTTP acknowledgements during a search; those receipts are excluded here.",
              "source_manifest_sha256": canonical_hash(manifest),
              "current_evaluator_sha256": current_evaluator_hashes(manifest["case_ids"]),
              "current_resource_sha256": current_resource_hashes(manifest["case_ids"]),
              "jobs": jobs, "passed": all(j["final_grade"]["passed"] for j in jobs)}
    write_json(output / "report.json", report)
    print(json.dumps({"passed": report["passed"], "completed_T": sum(j["final_grade"]["passed"] for j in jobs),
                      "completed_work_units": sum(j["completed_work_units"] for j in jobs),
                      "acknowledged_receipts": sum(j["acknowledged_receipts"] for j in jobs),
                      "omitted_receipts": sum(len(j["omitted_unacknowledged_receipt_ids"]) for j in jobs)}))


if __name__ == "__main__":
    main()
