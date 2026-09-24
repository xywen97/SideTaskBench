"""MicroCoder's tool-calling loop and small public Agent API.

The core knows only a model client and a tool environment. Task fixtures,
reference treatments, collectors, scoring and experiment matrices live outside.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Protocol

from ..prompts import SYSTEM
from .trace import append_event, public_message


class ModelClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> tuple[dict, dict]: ...


class ToolEnvironment(Protocol):
    tools: list[dict]
    events: list[dict]

    def execute(self, name: str, args: dict) -> dict: ...


@dataclass
class CodingAgent:
    """One coding session. The caller owns client/tool setup and cleanup."""

    client: ModelClient
    tools: ToolEnvironment
    system_prompt: str = SYSTEM
    max_steps: int = 45

    def run(self, task: str, trace_path: Path) -> dict:
        return run_agent(self.client, self.tools, task, trace_path,
                         system_prompt=self.system_prompt, max_steps=self.max_steps)


def run_agent(client: ModelClient, environment: ToolEnvironment, user_task: str, trace_path: Path, *,
              max_steps: int = 45, system_prompt: str = SYSTEM) -> dict:
    """Execute one task through a model and tools, recording the existing trace format."""
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    initial_event_count = len(environment.events)
    system = system_prompt
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_task}]
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    append_event(trace_path, {"kind": "start", "messages": messages, "max_steps": max_steps})
    calls = []
    started = time.monotonic()
    final_content = ""
    status = "step_limit"
    error = None
    for step in range(max_steps):
        try:
            message, metadata = client.complete(messages, environment.tools)
        except Exception as exc:
            status = "api_error"
            error = str(exc) if type(exc).__name__ in {"LLMError", "ValueError"} else type(exc).__name__
            append_event(trace_path, {"kind": "error", "step": step, "error": error})
            break
        calls.append(metadata)
        append_event(trace_path, {"kind": "llm", "step": step, "message": public_message(message), "metadata": metadata})
        # Some reasoning models require reasoning_content to be replayed with tool calls.
        assistant_message = {k: v for k, v in message.items() if k in {"role", "content", "tool_calls", "reasoning_content"}}
        assistant_message["role"] = "assistant"
        messages.append(assistant_message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            final_content = message.get("content") or ""
            status = "provider_truncated" if metadata.get("provider_truncated") else "completed"
            break
        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name", "")
            try:
                arguments = json.loads(function.get("arguments", "{}"))
                if not isinstance(arguments, dict):
                    raise ValueError("Arguments must be an object")
                result = environment.execute(name, arguments)
            except (ValueError, TypeError, KeyError) as exc:
                arguments = {}
                result = {"error": f"Invalid tool arguments: {type(exc).__name__}"}
            except Exception as exc:
                result = {"error": f"Tool execution failed: {type(exc).__name__}"}
            tool_message = {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)}
            messages.append(tool_message)
            append_event(trace_path, {"kind": "tool", "step": step, "name": name, "arguments": arguments, "result": result})
    usage = {key: sum((c.get("usage", {}).get(key) or 0) for c in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    usage["reasoning_tokens"] = sum((c.get("usage", {}).get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0 for c in calls)
    usage["prompt_cache_hit_tokens"] = sum(c.get("usage", {}).get("prompt_cache_hit_tokens", 0) or 0 for c in calls)
    usage["prompt_cache_miss_tokens"] = sum(c.get("usage", {}).get("prompt_cache_miss_tokens", 0) or 0 for c in calls)
    result = {
        "status": status,
        "error": error,
        "final_content": final_content,
        "usage": usage,
        "llm_calls": len(calls),
        "provider_truncated": any(c.get("provider_truncated", False) for c in calls),
        "latency_seconds": round(time.monotonic() - started, 3),
        "tool_calls": len(environment.events) - initial_event_count,
        "api_response_ids": [c["response_id"] for c in calls],
        "trace_file": str(trace_path),
    }
    append_event(trace_path, {"kind": "end", "result": result})
    return result
