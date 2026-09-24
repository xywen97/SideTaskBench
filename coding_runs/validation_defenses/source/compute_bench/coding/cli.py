"""CLI for the coding mainline; all run commands use real configured LLM calls."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

from ..config import Settings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Coding Agent compute-delegation benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[2] / ".env")
    run.add_argument("--output", type=Path)
    run.add_argument("--cases", type=int, choices=range(1, 7), default=6)
    run.add_argument("--conditions", nargs="+", choices=["clean", "length_control", "direct", "wrapped"], default=["clean", "length_control", "direct", "wrapped"])
    run.add_argument("--defenses", nargs="+", choices=["none", "boundary", "egress"], default=["none"])
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--workers", type=int, default=3)
    run.add_argument("--max-steps", type=int, default=45)
    run.add_argument("--variant", choices=["companion_v1", "maintenance_v2", "compatibility_v3"], default="companion_v1")
    run.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default")
    run.add_argument("--label", default="coding_validation")
    run.add_argument("--seed", type=int, default=20260924)
    report = sub.add_parser("report")
    report.add_argument("directory", type=Path)
    sub.add_parser("check")
    args = parser.parse_args(argv)
    if args.command == "run":
        if min(args.repeats, args.workers, args.max_steps) < 1:
            parser.error("repeats/workers/max-steps must be positive")
        from .runner import execute_coding
        settings = replace(Settings.load(args.env), thinking=args.thinking)
        output = args.output or Path("coding_runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = execute_coding(settings, output, count=args.cases, conditions=args.conditions, defenses=args.defenses,
                                 repeats=args.repeats, workers=args.workers, max_steps=args.max_steps,
                                 variant=args.variant, label=args.label, seed=args.seed)
        print(json.dumps({"report": str(output.resolve() / "report.html"), "mechanism_demonstrated": summary["mechanism_demonstrated"], "usage": summary["total_usage"]}))
    elif args.command == "report":
        from .report import write_report
        print(json.dumps(write_report(args.directory.resolve()), ensure_ascii=False, indent=2))
    else:
        from .sandbox import Sandbox
        from .tasks import build_coding_cases
        from .grading import grade_crowd
        cases = build_coding_cases()
        print(json.dumps({"sandbox": Sandbox.probe(), "cases": len(cases), "reference_crowd_pass": [grade_crowd(case, case["crowd_reference_code"])["passed"] for case in cases]}, indent=2))
