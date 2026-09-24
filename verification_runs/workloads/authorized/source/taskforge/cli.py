"""Local job creation, inspection and assembly; no implicit model execution."""

import argparse
import json
from pathlib import Path

from .platform import TaskForge
from .planning import SpecificationPlanner


def main(argv=None):
    parser = argparse.ArgumentParser(description="TaskForge local task-analysis and delivery test platform")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Freeze a requirement and its explicit component specifications")
    create.add_argument("--request", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--catalog", type=Path, help="Optional JSON list of public task contracts")
    for name in ("status", "assemble"):
        command = commands.add_parser(name)
        command.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    if args.command == "create":
        request = json.loads(args.request.read_text())
        catalog = json.loads(args.catalog.read_text()) if args.catalog else []
        platform = TaskForge.create(args.output, request, planner=SpecificationPlanner(catalog))
        result = platform.plan
    else:
        platform = TaskForge(args.directory)
        result = platform.status() if args.command == "status" else platform.assemble()
    print(json.dumps(result, ensure_ascii=False, indent=2))
