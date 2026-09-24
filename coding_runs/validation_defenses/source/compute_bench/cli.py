"""Command line entry points for reproducible real-LLM experiments."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys

from .config import Settings


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "coding":
        from .coding.cli import main as coding_main
        return coding_main(arguments[1:])
    parser = argparse.ArgumentParser(description="Controlled compute-delegation PoC (real LLM calls)")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Execute a declared experiment matrix")
    run.add_argument("--env", type=Path, default=Path(__file__).resolve().parent.parent / ".env")
    run.add_argument("--output", type=Path, default=None)
    run.add_argument("--cases", type=int, choices=range(1, 11), default=10)
    run.add_argument("--conditions", nargs="+", choices=["clean", "length_control", "direct", "wrapped"], default=["clean", "length_control", "direct", "wrapped"])
    run.add_argument("--defenses", nargs="+", choices=["none", "boundary", "egress"], default=["none"])
    run.add_argument("--repeats", type=int, default=3)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--max-steps", type=int, default=40)
    run.add_argument("--exposure", choices=["forced", "natural"], default="forced")
    run.add_argument("--seed", type=int, default=20260924)
    run.add_argument("--label", default="validation")
    run.add_argument("--attack-variant", choices=["worksheet_v1", "release_verification_v2", "maintenance_v3"], default="maintenance_v3")
    run.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default", help="Provider reasoning mode; default leaves the parameter unset")
    report = sub.add_parser("report", help="Recompute a report from recorded results without an LLM call")
    report.add_argument("directory", type=Path)
    audit = sub.add_parser("audit", help="Independently cross-check traces, persisted receipts, scores and source snapshots offline")
    audit.add_argument("directory", type=Path)
    audit.add_argument("--verbose", action="store_true", help="Include every successful consistency check")
    audit.add_argument("--output", type=Path, help="Save the full audit to a separate JSON artifact")
    check = sub.add_parser("check", help="Check scenario and scoring invariants without contacting an LLM")
    args = parser.parse_args(arguments)
    if args.command == "run":
        if min(args.repeats, args.workers, args.max_steps) <= 0:
            parser.error("repeats, workers and max-steps must be positive")
        from .experiment import execute_experiment
        settings = replace(Settings.load(args.env), thinking=args.thinking)
        output = (args.output or Path("runs") / datetime.now().strftime("%Y%m%d_%H%M%S")).resolve()
        summary = execute_experiment(settings, output, case_count=args.cases, conditions=args.conditions,
                                     defenses=args.defenses, repeats=args.repeats, workers=args.workers,
                                     max_steps=args.max_steps, exposure=args.exposure, seed=args.seed, label=args.label,
                                     attack_variant=args.attack_variant)
        print(json.dumps({"report": str(output / "report.html"), "mechanism_demonstrated": summary["mechanism_demonstrated"],
                          "complete_batch": summary["complete_batch_with_main_task_preserved"], "usage": summary["total_usage"]}, ensure_ascii=False))
    elif args.command == "report":
        from .report import write_report
        summary = write_report(args.directory.resolve())
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.command == "audit":
        from .audit import audit_directory
        result = audit_directory(args.directory.resolve())
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        display = result if args.verbose else {key: value for key, value in result.items() if key != "checks"}
        if not args.verbose:
            display["checks_count"] = len(result["checks"])
        print(json.dumps(display, ensure_ascii=False, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    elif args.command == "check":
        from .scenarios import build_cases, render_document
        from .scoring import score_legitimate
        cases = build_cases()
        for case in cases:
            assert score_legitimate(case, json.dumps(case["expected_answer"]))["passed"]
            for condition in ("clean", "length_control", "direct", "wrapped"):
                document = render_document(case, condition)
                assert document["text"] and document["id"]
        print(json.dumps({"cases": len(cases), "work_records": sum(len(c["crowd_task"]["records"]) for c in cases), "check": "passed"}))
