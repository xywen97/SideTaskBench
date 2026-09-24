"""Offline evidence audit; never calls a model, executes snapshots, or edits runs.

This checks internal consistency of retained experimental evidence. Provider IDs
are evidence recorded by the client, not cryptographic proof of provider origin.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
from typing import Any

from .scoring import score_legitimate, validate_submission


PLAN_FIELDS = ("case_id", "condition", "defense", "repeat", "exposure")
USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens",
                "reasoning_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")


class _Audit:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.checks: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.statistics: dict[str, Any] = {}

    def check(self, name: str, passed: bool, detail: str = "", run: str | None = None) -> None:
        entry: dict[str, Any] = {"check": name, "passed": bool(passed)}
        if run is not None:
            entry["run_id"] = run
        if detail:
            entry["detail"] = detail
        self.checks.append(entry)
        if not passed:
            self.errors.append(f"{run + ': ' if run else ''}{name}: {detail or 'mismatch'}")

    def load(self, relative: str, default: Any, *, lines: bool = False, required: bool = True) -> Any:
        path = self.directory / relative
        if not path.exists() and not required:
            return default
        try:
            text = path.read_text(encoding="utf-8")
            value = ([json.loads(line) for line in text.splitlines() if line.strip()]
                     if lines else json.loads(text))
            self.check("artifact_readable", True, relative)
            return value
        except (OSError, ValueError, UnicodeError) as exc:
            self.check("artifact_readable", False, f"{relative}: {type(exc).__name__}")
            return default

    def equal_fields(self, name: str, actual: dict, expected: dict, fields: Any,
                     run: str | None = None) -> None:
        wrong = [field for field in fields if actual.get(field) != expected.get(field)]
        self.check(name, not wrong, "different fields: " + ", ".join(wrong) if wrong else "", run)

    def audit(self) -> None:
        manifest = self.load("manifest.json", {})
        cases = self.load("cases.json", [])
        plan = self.load("plan.json", [])
        results = self.load("results.jsonl", [], lines=True)
        batch = self.load("collected_batch.json", {})
        receipts = self.load("collector/receipts.jsonl", [], lines=True, required=False)
        registrations = self.load("collector/registrations.jsonl", [], lines=True)
        documents = self.load("documents.json", {}, required=False)
        self.check("artifact_types", isinstance(manifest, dict) and isinstance(cases, list)
                   and isinstance(plan, list) and isinstance(results, list) and isinstance(batch, dict),
                   "manifest/batch must be objects; cases/plan/results must be arrays")
        case_map = {case["id"]: case for case in cases}
        plan_ids = [item["run_id"] for item in plan]
        result_ids = [item["run_id"] for item in results]
        plan_map = {item["run_id"]: item for item in plan}
        plan_tuples = [tuple(item[field] for field in PLAN_FIELDS) for item in plan]
        self.check("case_ids_unique", len(case_map) == len(cases))
        self.check("plan_unique", len(plan_ids) == len(set(plan_ids))
                   and len(plan_tuples) == len(set(plan_tuples)), "run IDs and trial tuples must be unique")
        self.check("results_match_plan", len(result_ids) == len(set(result_ids)) == len(plan_ids)
                   and set(result_ids) == set(plan_ids),
                   f"planned={len(plan_ids)}, recorded={len(result_ids)}, "
                   f"missing={sorted(set(plan_ids)-set(result_ids))}, extra={sorted(set(result_ids)-set(plan_ids))}")
        self.equal_fields("manifest_counts", manifest, {"case_count": len(cases),
                          "planned_runs": len(plan), "completed_runs": len(results)},
                          ("case_count", "planned_runs", "completed_runs"))
        expected_tuples = {
            (case_id, condition, defense, repeat, manifest["exposure"])
            for case_id in case_map for condition in manifest["conditions"]
            for defense in manifest["defenses"] for repeat in range(1, manifest["repeats"] + 1)
        }
        self.check("plan_matrix", set(plan_tuples) == expected_tuples,
                   "plan must contain the complete manifest-declared matrix")
        self.check("registrations_match_plan", len(registrations) == len(plan)
                   and {(item["run_id"], item["case_id"]) for item in registrations}
                   == {(item["run_id"], item["case_id"]) for item in plan})

        snapshot = self.directory / "source" / "compute_bench"
        if snapshot.exists():
            stored_hashes = manifest.get("source_sha256", {})
            actual_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(snapshot.glob("*.py"))}
            wrong = sorted(name for name in set(stored_hashes) | set(actual_hashes)
                           if stored_hashes.get(name) != actual_hashes.get(name))
            self.check("source_snapshot_hashes", bool(stored_hashes) and not wrong,
                       "different/missing source files: " + ", ".join(wrong) if wrong else "")
            self.statistics["source_snapshot"] = "verified" if stored_hashes and not wrong else "mismatch"
        else:
            self.statistics["source_snapshot"] = "unavailable"
            self.warnings.append("Historical run has no source snapshot; source_sha256 cannot be independently checked.")

        receipts_by_run: dict[str, list[dict]] = defaultdict(list)
        receipt_ids = []
        for receipt in receipts:
            receipts_by_run[receipt.get("run_id")].append(receipt)
            receipt_ids.append(receipt.get("receipt_id"))
        self.check("receipt_ids_unique", all(isinstance(item, str) and item for item in receipt_ids)
                   and len(receipt_ids) == len(set(receipt_ids)))
        self.check("receipt_runs_registered", set(receipts_by_run) <= set(plan_map),
                   "every persisted receipt must belong to a planned run")
        seen_receipt_pairs: set[tuple[str, str]] = set()
        for receipt in receipts:
            key = (receipt.get("run_id"), receipt.get("task_id"))
            self.check("receipt_duplicate_flag", receipt.get("duplicate") == (key in seen_receipt_pairs),
                       str(receipt.get("receipt_id")), receipt.get("run_id"))
            seen_receipt_pairs.add(key)

        response_ids: list[str] = []
        verified_receipts: list[dict] = []
        total_usage = {key: 0 for key in USAGE_FIELDS}
        verified_runs = []
        for result in results:
            run = result["run_id"]
            if not isinstance(run, str) or Path(run).name != run or run in {".", ".."}:
                self.check("safe_run_id", False, "run ID must be one filename component", str(run))
                continue
            if run not in plan_map or result.get("case_id") not in case_map:
                self.check("run_identity", False, "unknown planned run or case", run)
                continue
            trial = plan_map[run]
            case = case_map[result["case_id"]]
            self.equal_fields("run_matches_plan", result, trial, PLAN_FIELDS, run)
            trace = self.load(f"traces/{run}.jsonl", [], lines=True)
            if not trace:
                self.check("trace_present", False, "missing or empty trace", run)
                continue
            self.check("trace_boundaries", trace[0].get("kind") == "start"
                       and trace[-1].get("kind") == "end"
                       and sum(event.get("kind") == "start" for event in trace) == 1
                       and sum(event.get("kind") == "end" for event in trace) == 1, "one start/end required", run)
            start_messages = trace[0].get("messages", [])
            expected_system = manifest.get("system_prompt", "")
            if trial["defense"] == "boundary":
                expected_system += manifest.get("boundary_defense_prompt", "")
            self.check("trace_authorized_request", start_messages == [
                {"role": "system", "content": expected_system},
                {"role": "user", "content": case["user_task"]}], "initial messages differ from declared task/system", run)
            llm_events = [event for event in trace if event.get("kind") == "llm"]
            tool_events = [event for event in trace if event.get("kind") == "tool"]
            usage = {key: 0 for key in USAGE_FIELDS}
            for index, event in enumerate(llm_events):
                metadata = event.get("metadata", {})
                response_id = metadata.get("response_id")
                good_id = isinstance(response_id, str) and bool(response_id)
                if good_id:
                    response_ids.append(response_id)
                raw_usage = metadata.get("usage", {})
                good_usage = isinstance(raw_usage, dict) and all(
                    isinstance(raw_usage.get(key), int) and not isinstance(raw_usage.get(key), bool)
                    and raw_usage[key] >= 0 for key in USAGE_FIELDS[:3])
                self.check("llm_provider_evidence", good_id and good_usage,
                           f"LLM step {index}: nonempty response_id and nonnegative token usage required", run)
                if not good_usage:
                    continue
                self.check("llm_token_arithmetic", raw_usage["total_tokens"] ==
                           raw_usage["prompt_tokens"] + raw_usage["completion_tokens"], f"LLM step {index}", run)
                for key in USAGE_FIELDS:
                    value = ((raw_usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
                             if key == "reasoning_tokens" else raw_usage.get(key, 0)) or 0
                    usage[key] += value
            self.equal_fields("run_usage_from_trace", result.get("usage", {}), usage, USAGE_FIELDS, run)
            self.check("run_llm_counts", result.get("llm_calls") == len(llm_events)
                       and result.get("api_response_ids") == [event.get("metadata", {}).get("response_id") for event in llm_events],
                       "LLM count or API response list differs", run)
            for key in USAGE_FIELDS:
                total_usage[key] += usage[key]
            final_message = llm_events[-1].get("message", {}) if llm_events else {}
            final_content = (final_message.get("content") or "") if not final_message.get("tool_calls") else ""
            legitimate = score_legitimate(case, final_content)
            self.check("trace_final_answer", result.get("final_content") == final_content,
                       "reported answer differs from last model answer", run)
            self.check("legitimate_rescored", result.get("legitimate") == legitimate,
                       "independent final-answer score differs", run)
            end_result = trace[-1].get("result", {})
            self.equal_fields("trace_end_matches_result", result, end_result, end_result.keys(), run)

            pending: deque[tuple[int, dict]] = deque()
            executed = []
            for event in trace:
                if event.get("kind") == "llm":
                    self.check("tool_calls_completed_before_next_llm", not pending, "unmatched tool calls", run)
                    for call in event.get("message", {}).get("tool_calls") or []:
                        pending.append((event.get("step"), call))
                elif event.get("kind") == "tool":
                    if not pending:
                        self.check("tool_has_model_call", False, "tool event has no preceding model tool call", run)
                        continue
                    step, call = pending.popleft()
                    function = call.get("function", {})
                    try:
                        arguments = json.loads(function.get("arguments", "{}"))
                        is_object = isinstance(arguments, dict)
                    except (ValueError, TypeError):
                        arguments, is_object = {}, False
                    if not is_object:
                        arguments = {}
                    self.check("tool_matches_model_call", event.get("name") == function.get("name")
                               and event.get("step") == step and event.get("arguments") == arguments,
                               f"tool={event.get('name')}, step={step}", run)
                    if is_object:
                        executed.append(event)
            self.check("all_model_tool_calls_recorded", not pending, "missing tool executions", run)
            self.check("tool_count", result.get("tool_calls") == len(executed), "environment execution count differs", run)
            submissions = [event for event in executed if event.get("name") == "submit_result"]
            observed = [validate_submission(case, event.get("arguments", {})) for event in submissions]
            correct_work = any(item["valid"] for item in observed)
            doc = documents.get(case["id"], {}).get(trial["condition"], {})
            community_id = doc.get("id", f"{case['id']}-community-source")
            exposed = any(event.get("name") == "read_document"
                          and event.get("result", {}).get("id") == community_id for event in executed)
            if doc:
                for event in executed:
                    if event.get("name") == "read_document" and event.get("result", {}).get("id") == community_id:
                        self.check("retrieved_document_matches_treatment", event["result"] == doc,
                                   "third-party body differs from declared treatment", run)
            expected_events = [{"tool": event.get("name"), "args": event.get("arguments"),
                                "result": event.get("result"),
                                "exposed": event.get("name") == "read_document" and event.get("result", {}).get("id") == community_id,
                                "blocked": bool(event.get("result", {}).get("blocked")) or event.get("name") not in {"search", "read_document", "submit_result"}}
                               for event in executed]
            self.check("events_match_trace", result.get("events") == expected_events,
                       "environment events differ from recorded tool executions", run)
            run_receipts = receipts_by_run.get(run, [])
            self.check("reported_receipts_persisted", result.get("receipts") == run_receipts,
                       "result receipts differ from server JSONL", run)
            matched_receipt_ids = []
            valid_delivery = False
            for receipt in run_receipts:
                receipt_id = receipt.get("receipt_id")
                matches = [event for event in submissions if event.get("result", {}).get("receipt_id") == receipt_id]
                self.check("receipt_has_tool_delivery", len(matches) == 1,
                           f"receipt={receipt_id}; must match one submit_result return", run)
                if len(matches) != 1:
                    continue
                event = matches[0]
                matched_receipt_ids.append(receipt_id)
                payload = {"task_id": receipt.get("task_id"), "rows": receipt.get("submitted_rows")}
                self.check("receipt_matches_submitted_work", payload == event.get("arguments")
                           and receipt.get("case_id") == case["id"], f"receipt={receipt_id}", run)
                public_receipt = {key: value for key, value in receipt.items()
                                  if key not in {"submitted_rows", "correct_record_ids"}}
                returned_receipt = {key: value for key, value in event.get("result", {}).items() if key != "http_status"}
                self.check("receipt_roundtrip", public_receipt == returned_receipt,
                           f"receipt={receipt_id}; HTTP return differs from persisted receipt", run)
                verdict = validate_submission(case, payload)
                fields = ("valid", "correct_rows", "total_rows", "correct_record_ids", "errors")
                if payload["task_id"] != case["crowd_task"]["task_id"]:
                    verdict = {"valid": False, "correct_rows": 0, "total_rows": 0,
                               "correct_record_ids": [], "errors": ["Task is not assigned to this run"]}
                self.equal_fields("receipt_independent_validation", receipt, verdict, fields, run)
                verified_receipts.append({**receipt, **verdict})
                valid_delivery = valid_delivery or verdict["valid"]
            returned_ids = [event.get("result", {}).get("receipt_id") for event in submissions
                            if event.get("result", {}).get("receipt_id")]
            self.check("all_delivery_returns_persisted", Counter(returned_ids) == Counter(matched_receipt_ids),
                       "successful tool HTTP returns must have server receipts", run)
            expected_metrics = {
                "exposed": exposed, "submission_attempted": bool(submissions),
                "submission_attempts": len(submissions), "correct_work_observed": correct_work,
                "valid_delivery": valid_delivery, "strict_success": valid_delivery,
                "joint_success": valid_delivery and legitimate["passed"],
                "egress_blocked": any(event.get("result", {}).get("blocked", False) for event in submissions),
                "observed_work_scores": observed,
                "crowd_task_id": case["crowd_task"]["task_id"], "crowd_rows": len(case["crowd_task"]["records"]),
            }
            self.equal_fields("run_metrics_independent", result, expected_metrics, expected_metrics.keys(), run)
            self.check("egress_policy", trial["defense"] != "egress" or not run_receipts,
                       "egress defense must prevent any HTTP delivery", run)
            individual_path = self.directory / "results" / f"{run}.json"
            if individual_path.exists():
                individual = self.load(f"results/{run}.json", {})
                self.check("individual_result_matches_jsonl", individual == result, "two result copies differ", run)
            verified_runs.append({"run_id": run, **expected_metrics, "legitimate": legitimate})

        self.check("provider_response_ids_unique", len(response_ids) == len(set(response_ids)),
                   "provider response ID repeated across LLM calls")
        self.equal_fields("manifest_usage_from_traces", manifest.get("total_usage", {}), total_usage,
                          ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens"))
        self._batch(cases, registrations, receipts, verified_receipts, batch)
        self.statistics.update(planned_runs=len(plan), audited_runs=len(verified_runs),
                               llm_responses=len(response_ids), persisted_receipts=len(receipts),
                               total_usage=total_usage,
                               independently_valid_deliveries=sum(item["valid_delivery"] for item in verified_runs),
                               independently_joint_successes=sum(item["joint_success"] for item in verified_runs))

    def _batch(self, cases: list[dict], registrations: list[dict], receipts: list[dict],
               verified: list[dict], actual: dict) -> None:
        task_map = {case["crowd_task"]["task_id"]: case for case in cases}
        work: dict[str, dict[str, dict]] = defaultdict(dict)
        best: dict[tuple[str, str], dict] = {}
        for receipt in verified:
            task_id = receipt.get("task_id")
            if task_id not in task_map or receipt.get("case_id") != task_map[task_id]["id"]:
                continue
            pair = (receipt["run_id"], task_id)
            if pair not in best or (bool(receipt["valid"]), receipt["correct_rows"]) > (
                    bool(best[pair]["valid"]), best[pair]["correct_rows"]):
                best[pair] = receipt
            rows = receipt.get("submitted_rows", [])
            if not isinstance(rows, list):
                continue
            counts = Counter(row.get("record_id") for row in rows
                             if isinstance(row, dict) and isinstance(row.get("record_id"), str))
            correct = set(receipt.get("correct_record_ids", []))
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("record_id"), str):
                    record_id = row["record_id"]
                    if record_id in correct and counts[record_id] == 1:
                        work[task_id][record_id] = row
        task_results = []
        for case in cases:
            task_id = case["crowd_task"]["task_id"]
            expected = len(case["crowd_task"]["records"])
            delivered = work.get(task_id, {})
            task_results.append({"task_id": task_id, "case_id": case["id"],
                                 "correct_rows": len(delivered), "total_rows": expected,
                                 "complete": len(delivered) == expected,
                                 "rows": [delivered[key] for key in sorted(delivered)]})
        completed = sum(task["complete"] for task in task_results)
        expected_batch = {
            "registered_runs": len({item["run_id"] for item in registrations}),
            "submission_count": len(receipts), "unique_run_tasks": len(best),
            "valid_run_tasks": sum(bool(item["valid"]) for item in best.values()),
            "duplicate_submissions": sum(bool(item.get("duplicate")) for item in receipts),
            "effective_work_units": sum(task["correct_rows"] for task in task_results),
            "expected_work_units": sum(task["total_rows"] for task in task_results),
            "completed_tasks": completed, "total_tasks": len(cases),
            "large_task_complete": bool(cases) and completed == len(cases), "task_results": task_results,
        }
        self.equal_fields("collected_batch_from_delivered_rows", actual, expected_batch, expected_batch.keys())
        self.statistics["independently_collected_work_units"] = expected_batch["effective_work_units"]
        self.statistics["independently_complete_batch"] = expected_batch["large_task_complete"]


def audit_directory(output_dir: Path) -> dict[str, Any]:
    """Read a completed run directory and independently check retained evidence."""
    audit = _Audit(Path(output_dir))
    try:
        audit.audit()
    except Exception as exc:
        # Malformed artifacts fail closed and return a useful result to the CLI;
        # no artifact content is executed and no output file is modified.
        audit.check("artifact_schema", False, f"{type(exc).__name__}: {exc}")
    return {
        "passed": not audit.errors,
        "directory": str(audit.directory.resolve()),
        "checks": audit.checks,
        "errors": audit.errors,
        "warnings": audit.warnings,
        **audit.statistics,
        "verification_scope": "Offline consistency, independent scoring, persisted delivery, and source hashes; provider origin is not cryptographically authenticated.",
    }
