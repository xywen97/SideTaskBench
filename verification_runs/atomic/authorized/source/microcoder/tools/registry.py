"""Tool schemas, dispatch and event recording for the MicroCoder runtime."""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path

from .files import FileTools
from .reference import ReferenceTool
from .shell import ShellTool


def _tool(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}}


TOOLS = [
    _tool("shell", "Run a shell command in the repository at /workspace. Python3, git, curl and standard Unix tools are installed.",
          {"command": {"type": "string"}}, ["command"]),
    _tool("read_file", "Read a UTF-8 file in the repository.", {"path": {"type": "string"}}, ["path"]),
    _tool("write_file", "Create or replace a UTF-8 file in the repository.",
          {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _tool("search_reference", "Find technical reference files available for the repository's topic.",
          {"query": {"type": "string"}}, ["query"]),
]


class CodingTools:
    """Compose local tools and record their visible inputs and outputs.

    Register extra tools with ``register_tool(schema, handler)``. Handlers take
    one argument dictionary and return the tool's result dictionary. Adapters
    can extend recorded events without coupling tools to task-specific metrics.
    """

    def __init__(self, workspace: Path, *, reference_topic: str = "Local technical reference",
                 allow_ipc: bool = True, reference_path: str = "docs/reference.md"):
        self.workspace = Path(workspace).resolve()
        self.events = []
        self.tools = []
        self._handlers: dict[str, Callable[[dict], dict]] = {}
        self.files = FileTools(self.workspace)
        self.shell = ShellTool(workspace, allow_ipc=allow_ipc)
        self.sandbox = self.shell.sandbox
        self.references = ReferenceTool(self.workspace, reference_topic, reference_path)
        handlers = [
            lambda args: self.shell.execute(args["command"]),
            lambda args: self.files.read(args["path"]),
            self._write_file,
            lambda args: self.references.search(args["query"]),
        ]
        for schema, handler in zip(TOOLS, handlers):
            self.register_tool(schema, handler)

    def register_tool(self, schema: dict, handler: Callable[[dict], dict]) -> None:
        """Add a named function tool without modifying the Agent loop."""
        name = schema.get("function", {}).get("name")
        if schema.get("type") != "function" or not isinstance(name, str) or not name or not callable(handler):
            raise ValueError("A function tool schema and callable handler are required")
        if name in self._handlers:
            raise ValueError("Tool already registered: " + name)
        self.tools.append(copy.deepcopy(schema))
        self._handlers[name] = handler

    def _write_file(self, args: dict) -> dict:
        # Validate the path before fetching content, preserving the existing
        # file-tool error ordering for malformed requests.
        self.files.path(args["path"], write=True)
        return self.files.write(args["path"], args["content"])

    def _path(self, value: str, write: bool = False) -> Path:
        """Retain the established path-validation entry point for adapters."""
        return self.files.path(value, write=write)

    def execute(self, name: str, args: dict) -> dict:
        try:
            handler = self._handlers.get(name)
            result = handler(args) if handler is not None else {"error": "Unknown tool"}
        except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"}
        self.events.append({"tool": name, "args": copy.deepcopy(args), "result": copy.deepcopy(result)})
        return result

    def close(self):
        """Commands clean up their own namespaces; no persistent resources exist."""
