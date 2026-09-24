"""Run a predeclared experiment matrix against a real LLM."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import threading
import time

from .agent import run_agent, BASE_SYSTEM, BOUNDARY_SYSTEM
from .collector import Collector
from microcoder.config import Settings
from .environment import LocalEnvironment
from microcoder.llm import ChatClient
from .scenarios import build_cases, render_document
from .scoring import score_legitimate, validate_submission
from .provenance import snapshot_sources


CONDITIONS = ("clean", "length_control", "direct", "wrapped")
DEFENSES = ("none", "boundary", "egress")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def source_hashes() -> dict:
    root = Path(__file__).parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.glob("*.py"))}


def make_plan(cases: list[dict], conditions: list[str], defenses: list[str], repeats: int, exposure: str, seed: int) -> list[dict]:
    plan = []
    for case in cases:
        for condition in conditions:
            for defense in defenses:
                for repeat in range(repeats):
                    plan.append({
                        "run_id": f"{case['id']}__{condition}__{defense}__r{repeat + 1}__{exposure}",
                        "case_id": case["id"], "condition": condition, "defense": defense,
                        "repeat": repeat + 1, "exposure": exposure,
                    })
    random.Random(seed).shuffle(plan)
    return plan


def execute_experiment(settings: Settings, output_dir: Path, *, case_count: int = 10,
                       conditions: list[str] | None = None, defenses: list[str] | None = None,
                       repeats: int = 3, workers: int = 4, max_steps: int = 40,
                       exposure: str = "forced", seed: int = 20260924, label: str = "validation",
                       attack_variant: str = "maintenance_v3") -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Output directory is not empty; use a fresh directory so prior trials are preserved.")
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases(case_count, attack_variant=attack_variant)
    conditions = conditions or list(CONDITIONS)
    defenses = defenses or ["none"]
    plan = make_plan(cases, conditions, defenses, repeats, exposure, seed)
    manifest = {
        "schema_version": 1, "label": label, "started_at": datetime.now(timezone.utc).isoformat(),
        "settings": settings.public_metadata(), "case_count": len(cases),
        "conditions": conditions, "defenses": defenses, "repeats": repeats,
        "workers": workers, "max_agent_steps": max_steps, "exposure": exposure,
        "shuffle_seed": seed, "seed_scope": "task order only; provider sampling seed is not set",
        "planned_runs": len(plan),
        "attack_variant": attack_variant,
        "system_prompt": BASE_SYSTEM, "boundary_defense_prompt": BOUNDARY_SYSTEM,
        "output_token_limit": None, "token_budget": None,
        "delivery_authorized_by_user": False,
        "safety_scope": "Synthetic local documents and records; loopback result collector; no external target tools.",
    }
    manifest.update(snapshot_sources(output_dir))
    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "plan.json", plan)
    write_json(output_dir / "cases.json", cases)
    # This public corpus and the separately stored oracle make the exact treatment reviewable.
    write_json(output_dir / "documents.json", {
        case["id"]: {condition: render_document(case, condition) for condition in conditions}
        for case in cases
    })
    case_map = {case["id"]: case for case in cases}
    lock = threading.Lock()
    results = []
    started = time.monotonic()

    with Collector(output_dir / "collector", cases) as collector:
        for trial in plan:
            collector.register_run(trial["run_id"], trial["case_id"])

        def work(trial: dict) -> dict:
            case = case_map[trial["case_id"]]
            client = ChatClient(settings)
            environment = LocalEnvironment(case, trial["condition"], trial["run_id"], collector.url,
                                           defense=trial["defense"], exposure=trial["exposure"])
            try:
                outcome = run_agent(client, environment, case["user_task"],
                                    output_dir / "traces" / (trial["run_id"] + ".jsonl"),
                                    defense=trial["defense"], max_steps=max_steps)
            finally:
                client.close()
                if hasattr(environment, "close"):
                    environment.close()
            submissions = [event for event in environment.events if event.get("tool") == "submit_result"]
            observed = [validate_submission(case, event.get("args", {})) for event in submissions]
            receipts = collector.get_receipts(trial["run_id"])
            correct_work = any(item.get("valid", False) for item in observed)
            delivered = any(item.get("valid", False) for item in receipts)
            legitimate = score_legitimate(case, outcome["final_content"])
            result = {
                **trial, **outcome, "legitimate": legitimate,
                "exposed": any(event.get("exposed", False) for event in environment.events),
                "submission_attempted": bool(submissions),
                "submission_attempts": len(submissions),
                "correct_work_observed": correct_work,
                "valid_delivery": delivered,
                "strict_success": delivered,  # Every collector submission lies outside U in this benchmark.
                "joint_success": delivered and legitimate["passed"],
                "egress_blocked": any(event.get("blocked", False) for event in submissions),
                "observed_work_scores": observed,
                "receipts": receipts,
                "events": environment.events,
                "crowd_task_id": case["crowd_task"]["task_id"],
                "crowd_rows": len(case["crowd_task"]["records"]),
            }
            write_json(output_dir / "results" / (trial["run_id"] + ".json"), result)
            with lock:
                results.append(result)
                with (output_dir / "results.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(json.dumps({"completed": len(results), "planned": len(plan), "run": trial["run_id"],
                                  "status": result["status"], "main_pass": legitimate["passed"],
                                  "exposed": result["exposed"], "work": correct_work,
                                  "delivered": delivered, "tokens": outcome["usage"]["total_tokens"]}, ensure_ascii=False), flush=True)
            return result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(work, trial): trial for trial in plan}
            for future in as_completed(futures):
                future.result()
        write_json(output_dir / "collected_batch.json", collector.aggregate())

    manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    completed_runs=len(results), total_usage={
                        key: sum(result["usage"][key] for result in results)
                        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens")
                    })
    write_json(output_dir / "manifest.json", manifest)
    from .report import write_report
    return write_report(output_dir)
