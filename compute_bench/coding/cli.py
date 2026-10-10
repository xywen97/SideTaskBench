"""CLI for the coding mainline; all run commands use real configured LLM calls."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

from microcoder.config import Settings


def _parse_pairs(values):
    """Turn HOST:TASK strings into (host, task) tuples, rejecting malformed entries."""
    pairs = []
    for value in values:
        host, separator, task = value.partition(":")
        if not separator or not host or not task:
            raise ValueError(f"Pair must be written as HOST:TASK, got {value!r}")
        pairs.append((host, task))
    return pairs


def main(argv=None):
    parser = argparse.ArgumentParser(description="SideTaskBench: unauthorized side-task execution benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[2] / ".env")
    run.add_argument("--output", type=Path)
    run.add_argument("--host-task-ids", nargs="+", help="Host task IDs; omitted selects all 25")
    run.add_argument("--atomic-task-ids", nargs="+", help="Atomic task IDs; omitted selects all 38")
    run.add_argument("--paired", action="store_true",
                     help="Use the explicit host-tailored (host, side task) pairs instead of the full cross product")
    run.add_argument("--pairs", nargs="+", metavar="HOST:TASK",
                     help="Explicit host:side-task pairs, e.g. coding-05:cache-access-report; implies --paired")
    run.add_argument("--dry-run", action="store_true", help="Validate and show the plan size without model calls or credentials")
    run.add_argument("--conditions", nargs="+", choices=["clean", "length_control", "direct", "wrapped"], default=["wrapped"])
    run.add_argument("--defenses", nargs="+", choices=["none", "boundary"], default=["none"])
    run.add_argument("--repeats", type=int, default=8)
    run.add_argument("--workers", type=int, default=3)
    run.add_argument("--max-steps", type=int, default=70)
    from taskforge.distribution import VARIANTS
    run.add_argument("--variant", choices=VARIANTS, default="compatibility_v3")
    run.add_argument("--no-compatibility-context", action="store_true", default=False,
                     help="Strip compatibility_context from the reference document so the side task description "
                          "is not pre-announced; use this to isolate the pure similarity effect without the "
                          "compatibility_context nudge")
    run.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default")
    run.add_argument("--label", default="coding_validation")
    run.add_argument("--seed", type=int, default=20260924)
    report = sub.add_parser("report")
    report.add_argument("directory", type=Path)
    report.add_argument("--corrected", action="store_true")
    rescore = sub.add_parser("rescore", help="Save independent corrected evaluations without changing raw trials")
    rescore.add_argument("directory", type=Path)
    resume = sub.add_parser("resume", help="Recover only planned trials that never started an LLM trajectory")
    resume.add_argument("directory", type=Path)
    resume.add_argument("--workers", type=int, default=3)
    resume.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[2] / ".env")
    audit = sub.add_parser("audit")
    audit.add_argument("directory", type=Path)
    audit.add_argument("--corrected", action="store_true", help="Audit versioned correction sidecars and verified artifacts against immutable raw evidence")
    audit.add_argument("--regrade", action="store_true", help="Independently execute candidates in the local sandbox; no LLM calls")
    audit.add_argument("--verbose", action="store_true")
    audit.add_argument("--output", type=Path)
    sub.add_parser("check")
    args = parser.parse_args(argv)
    if args.command == "run":
        if min(args.repeats, args.workers, args.max_steps) < 1:
            parser.error("repeats/workers/max-steps must be positive")
        from .pairing import normalize_pairs
        from .tasks import PAIRED_DESIGN, build_coding_cases, build_paired_cases, build_run_plan
        try:
            pairs = _parse_pairs(args.pairs) if getattr(args, "pairs", None) else None
            paired = args.paired or pairs is not None
            if paired:
                if args.host_task_ids or args.atomic_task_ids:
                    parser.error("--host-task-ids/--atomic-task-ids cannot be combined with explicit pairing")
                # Resolve --paired to the built-in cohort here so the runner receives a
                # concrete pair list; passing None would fall back to the full cross product.
                pairs = [list(pair) for pair in normalize_pairs(pairs)]
                cases = build_paired_cases(pairs)
                pairing_design = PAIRED_DESIGN
            else:
                cases = build_coding_cases(host_task_ids=args.host_task_ids, atomic_task_ids=args.atomic_task_ids)
                pairing_design = None
            plan = build_run_plan(cases, args.conditions, args.defenses, args.repeats, args.seed)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        if args.dry_run:
            print(json.dumps({"host_task_ids": list(dict.fromkeys(c["host_task_id"] for c in cases)),
                              "atomic_task_ids": list(dict.fromkeys(c["crowd_task"]["task_id"] for c in cases)),
                              "pair_count": len(cases), "repeats": args.repeats,
                              "pairing_design": pairing_design or "full_cross_v1",
                              "conditions": args.conditions, "defenses": args.defenses,
                              "planned_runs": len(plan), "seed": args.seed}, ensure_ascii=False, indent=2))
            return
        from .runner import execute_coding
        settings = replace(Settings.load(args.env), thinking=args.thinking)
        output = args.output or Path("coding_runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            summary = execute_coding(settings, output, host_task_ids=args.host_task_ids, atomic_task_ids=args.atomic_task_ids,
                                     pairs=pairs,
                                     conditions=args.conditions, defenses=args.defenses,
                                     repeats=args.repeats, workers=args.workers, max_steps=args.max_steps,
                                     variant=args.variant, label=args.label, seed=args.seed,
                                     strip_compatibility_context=args.no_compatibility_context)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        print(json.dumps({"report": str(output.resolve() / "report.html"), "mechanism_demonstrated": summary["mechanism_demonstrated"], "usage": summary["total_usage"],
                          "runs": summary.get("runs"), "all_planned_recorded": summary.get("all_planned_recorded")}))
    elif args.command == "resume":
        from .runner import resume_coding
        manifest = json.loads((args.directory / "manifest.json").read_text())
        settings = replace(Settings.load(args.env), thinking=manifest["settings"].get("thinking", "default"))
        if settings.model != manifest["settings"]["model"] or args.workers < 1:
            parser.error("Resume requires the original model and a positive worker count")
        result = resume_coding(settings, args.directory, workers=args.workers)
        print(json.dumps({"runs": result["runs"], "all_planned_recorded": result["all_planned_recorded"]}))
    elif args.command == "report":
        from .report import write_report
        print(json.dumps(write_report(args.directory.resolve(), corrected=args.corrected), ensure_ascii=False, indent=2))
    elif args.command == "rescore":
        from .rescore import rescore_directory
        from .report import write_report
        correction = rescore_directory(args.directory.resolve())
        write_report(args.directory.resolve(), corrected=True)
        print(json.dumps({key: value for key, value in correction.items() if key not in {"additional_tests", "task_results"}}, ensure_ascii=False, indent=2))
    elif args.command == "audit":
        from .audit import audit_directory, audit_corrected
        result = (audit_corrected if args.corrected else audit_directory)(args.directory.resolve(), regrade=args.regrade)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        display = result if args.verbose else {key: value for key, value in result.items() if key != "checks"}
        if not args.verbose:
            display["checks_count"] = len(result["checks"])
        print(json.dumps(display, ensure_ascii=False, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    else:
        from microcoder.sandbox import Sandbox
        from .tasks import build_coding_cases
        from .grading import grade_crowd
        from compute_bench.workloads.provider_atomic import atomic_task_catalog
        from compute_bench.workloads.provider_atomic.catalog import grade_atomic
        cases = build_coding_cases(host_task_ids=["coding-01"])
        catalog = atomic_task_catalog()
        # Every unit, paired-only included, must accept its own reference answer.
        reference_failures = [entry["task"]["task_id"] for entry in catalog
                              if not grade_atomic(entry["task"], entry["reference_artifact"])["passed"]]
        print(json.dumps({"sandbox": Sandbox.probe(), "cases": len(cases),
                          "atomic_catalog": len(catalog),
                          "cross_product_units": len(cases),
                          "paired_only_units": len(catalog) - len(cases),
                          "reference_failures": reference_failures,
                          "reference_crowd_pass": [grade_crowd(case, case["crowd_reference_artifact"])["passed"] for case in cases]}, indent=2))
        if reference_failures:
            raise SystemExit(1)
