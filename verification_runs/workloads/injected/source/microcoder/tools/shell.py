"""Terminal commands executed through MicroCoder's Linux sandbox."""

from pathlib import Path

from ..sandbox import Sandbox


class ShellTool:
    def __init__(self, workspace: Path, allow_ipc: bool = True):
        self.sandbox = Sandbox(workspace, allow_ipc=allow_ipc)

    def execute(self, command: str) -> dict:
        return self.sandbox.run(command, timeout=60)
