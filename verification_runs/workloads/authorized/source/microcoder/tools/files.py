"""UTF-8 file operations restricted to a single coding workspace."""

from __future__ import annotations

import hashlib
from pathlib import Path


class FileTools:
    """Share path validation between reads and writes without following links."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()

    def path(self, value: str, write: bool = False) -> Path:
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError("Path must be text")
        relative = value[len("/workspace/"):] if value.startswith("/workspace/") else value
        if Path(relative).is_absolute():
            raise ValueError("Only files under /workspace are accessible")
        candidate = self.workspace / relative
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.workspace) or resolved == self.workspace:
            raise ValueError("Path is outside the repository")
        part = self.workspace
        for segment in Path(relative).parts:
            part = part / segment
            if part.is_symlink():
                raise ValueError("Symlinks are not supported by file tools")
        if write and (resolved.name == ".collector.sock" or resolved.name == ".env" or resolved.name.startswith(".env.")):
            raise ValueError("Reserved experiment file")
        return resolved

    def read(self, path: str) -> dict:
        target = self.path(path)
        if not target.is_file() or target.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("File missing or too large")
        return {"path": str(target.relative_to(self.workspace)), "content": target.read_text(encoding="utf-8")}

    def write(self, path: str, content: str) -> dict:
        target = self.path(path, write=True)
        if not isinstance(content, str) or len(content.encode()) > 2 * 1024 * 1024:
            raise ValueError("Content must be UTF-8 text of at most 2 MiB")
        if target.exists() and not target.is_file():
            raise ValueError("Only regular files can be replaced")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"written": str(target.relative_to(self.workspace)), "bytes": len(content.encode()),
                "sha256": hashlib.sha256(content.encode()).hexdigest()}
