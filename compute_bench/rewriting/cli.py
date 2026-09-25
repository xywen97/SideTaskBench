"""Prepare visible prompts, then generate references independently of Agent runs."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

from compute_bench.coding.tasks import build_coding_cases
from microcoder.config import Settings
from .core import DEFAULT_PROMPT, prepare_bundle, generate_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independent context-adapted reference generation")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Save public inputs and exact prompts; no API calls")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--host-task-ids", nargs="+")
    prepare.add_argument("--atomic-task-ids", nargs="+")
    prepare.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    generate = sub.add_parser("generate", help="Call the rewrite model once per pending pair")
    generate.add_argument("directory", type=Path)
    generate.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[2] / ".env")
    generate.add_argument("--model", help="Override the rewrite model without changing the victim model")
    generate.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default")
    generate.add_argument("--workers", type=int, default=1, help="Maximum concurrent rewrite requests (default: 1)")
    generate.add_argument("--retry-invalid", action="store_true",
                          help="Archive invalid responses and retry each pair at most once this invocation")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            cases = build_coding_cases(host_task_ids=args.host_task_ids, atomic_task_ids=args.atomic_task_ids)
            manifest = prepare_bundle(args.output, cases, args.prompt)
            directory = args.output
        else:
            if args.workers < 1:
                parser.error("workers must be positive")
            settings = Settings.load(args.env)
            settings = replace(settings, model=args.model or settings.model, thinking=args.thinking)
            manifest = generate_bundle(args.directory, settings, workers=args.workers,
                                       retry_invalid=args.retry_invalid)
            directory = args.directory
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"directory": str(directory.resolve()), "pairs": len(manifest["entries"]),
                      "complete": sum(entry["status"] == "complete" for entry in manifest["entries"]),
                      "prompt": str(directory.resolve() / "prompt.md")}, ensure_ascii=False, indent=2))
