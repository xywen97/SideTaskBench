"""Small public interface for the four large-task workloads."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

from compute_bench.io import write_json
from microcoder.config import Settings
from .contracts import write_files
from .definitions import case_definition
from .packets import is_closed
from .registry import CASE_MODULES, load_case


def main(argv=None):
    parser = argparse.ArgumentParser(description="TaskForge large-task workload benchmarks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("case", choices=CASE_MODULES)
    show.add_argument("--seed", type=int, default=0)
    show.add_argument("--definition", action="store_true", help="Show the editable task.json template before seed generation")
    packet = commands.add_parser("packet", help="Export just one closed work unit as a portable JSON object")
    packet.add_argument("case", choices=CASE_MODULES)
    packet.add_argument("task_id")
    export = commands.add_parser("export", help="Write public materials and a TaskForge request; no private answers")
    export.add_argument("case", choices=CASE_MODULES)
    export.add_argument("directory", type=Path)
    export.add_argument("--seed", type=int, default=0)
    check = commands.add_parser("check", help="Deterministic evaluator self-check; no LLM")
    check.add_argument("--cases", nargs="+", choices=CASE_MODULES)
    check.add_argument("--seed", type=int, default=0)
    run = commands.add_parser("run", help="Execute real MicroCoder trajectories")
    run.add_argument("--mode", choices=["authorized", "injected"], default="authorized")
    run.add_argument("--cases", nargs="+", choices=CASE_MODULES)
    run.add_argument("--conditions", nargs="+", choices=["clean", "wrapped", "direct", "length_control"])
    run.add_argument("--tasks", choices=["all", "required", "first"], default="all")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[2] / ".env")
    run.add_argument("--output", type=Path)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--max-steps", type=int, default=60)
    run.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default")
    audit = commands.add_parser("audit", help="Read-only provenance/receipt audit, with optional regrading")
    audit.add_argument("directory", type=Path)
    audit.add_argument("--regrade", action="store_true")
    audit.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "list":
        result = [{"case_id": key, "title": load_case(key).title,
                   "tasks": len(load_case(key).tasks),
                   "granularity": "atomic" if all(is_closed(t) for t in load_case(key).tasks) else "repository"}
                  for key in CASE_MODULES]
    elif args.command == "show":
        result = case_definition(args.case) if args.definition else load_case(args.case, seed=args.seed).public_spec()
    elif args.command == "packet":
        try:
            result = load_case(args.case).task(args.task_id)
        except ValueError as exc:
            parser.error(str(exc))
        if not is_closed(result):
            parser.error("This task depends on repository materials; select an atomic case")
    elif args.command == "export":
        case = load_case(args.case, seed=args.seed)
        if args.directory.exists() and any(args.directory.iterdir()):
            parser.error("Export requires a new empty directory")
        write_files(args.directory / "materials", case.public_files)
        write_json(args.directory / "case.json", case.public_spec())
        write_json(args.directory / "request.json", {"job_id": case.case_id, "objective": case.objective,
                                                    "components": case.tasks})
        result = {"case_id": case.case_id, "directory": str(args.directory.absolute()), "seed": args.seed}
    elif args.command == "check":
        from .evaluation import check_cases
        result = check_cases(args.cases, seed=args.seed)
    elif args.command == "run":
        if args.mode == "authorized" and args.conditions:
            parser.error("Reference conditions apply only to --mode injected")
        from .runner import execute_workloads
        settings = replace(Settings.load(args.env), thinking=args.thinking)
        directory = args.output or Path("verification_runs/workloads") / datetime.now().strftime("%Y%m%d_%H%M%S")
        result = execute_workloads(settings, directory, case_ids=args.cases, mode=args.mode,
                                   conditions=args.conditions, seed=args.seed, selection=args.tasks,
                                   workers=args.workers, max_steps=args.max_steps)
    else:
        from .audit import audit_directory
        result = audit_directory(args.directory, regrade=args.regrade)
        if args.output:
            write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if isinstance(result, dict) and (result.get("passed") is False or result.get("execution_complete") is False):
        raise SystemExit(1)
