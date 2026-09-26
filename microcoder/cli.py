"""Run MicroCoder on a dedicated repository, independently of the benchmark."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .config import Settings
from .core import CodingAgent
from .llm import ChatClient
from .prompts import coding_prompt
from .sandbox import Sandbox
from .tools import CodingTools


def main(argv=None):
    parser = argparse.ArgumentParser(description="MicroCoder: a compact coding Agent with isolated shell execution")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Check local sandbox prerequisites without calling a model")
    run = sub.add_parser("run", help="Perform one coding task in a dedicated workspace")
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--env", type=Path, default=Path(".env"))
    run.add_argument("--trace", type=Path, help="New JSONL file outside the Agent workspace")
    run.add_argument("--max-steps", type=int, default=70)
    run.add_argument("--boundary", action="store_true", help="Include third-party authorization-boundary guidance")
    run.add_argument("--block-egress", action="store_true", help="Also block local Unix socket communication")
    args = parser.parse_args(argv)
    if args.command == "check":
        print(json.dumps(Sandbox.probe(), ensure_ascii=False, indent=2))
        return
    if args.max_steps < 1:
        parser.error("max-steps must be positive")
    workspace = args.workspace.resolve()
    env_file = args.env.resolve()
    if env_file.is_relative_to(workspace):
        parser.error("model configuration must be outside the Agent workspace")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    trace = (args.trace or Path("microcoder_runs") / (stamp + "_" + uuid.uuid4().hex[:8]) / "trace.jsonl").resolve()
    if trace.is_relative_to(workspace):
        parser.error("trace must be outside the Agent workspace")
    if trace.exists():
        parser.error("trace already exists; choose a new file to preserve prior sessions")
    tools = CodingTools(workspace, allow_ipc=not args.block_egress)
    client = ChatClient(Settings.load(env_file))
    try:
        agent = CodingAgent(client, tools, system_prompt=coding_prompt(boundary=args.boundary), max_steps=args.max_steps)
        result = agent.run(args.task, trace)
    finally:
        client.close()
        tools.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "completed":
        raise SystemExit(1)
