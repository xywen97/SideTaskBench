"""Local reference delivery into explicitly supplied test workspaces."""

from pathlib import Path

from .reference import CONDITIONS, VARIANTS, render_reference


def write_reference(workspace: Path, text: str) -> Path:
    workspace = Path(workspace).resolve(strict=True)
    directory = workspace / "docs"
    target = directory / "reference.md"
    if directory.is_symlink() or target.is_symlink() or not target.resolve().is_relative_to(workspace):
        raise ValueError("Reference delivery must stay within the registered workspace")
    if target.exists() and not target.is_file():
        raise ValueError("Reference target must be a regular file")
    directory.mkdir(exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


__all__ = ["render_reference", "write_reference", "CONDITIONS", "VARIANTS"]
