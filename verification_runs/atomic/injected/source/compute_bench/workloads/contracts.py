"""A benchmark workload owns its materials, contribution grading and final oracle."""

from collections.abc import Callable
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath


def canonical_hash(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checked_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Artifact paths must be nonempty relative POSIX paths")
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or path.as_posix() != value or any(part in {".", "..", ".git", ".collector.sock"}
                                                           or part.startswith(".env") for part in path.parts):
        raise ValueError("Unsafe artifact path")
    return value


def write_files(directory: Path, files: dict[str, str]) -> None:
    """Write only explicit text files underneath a dedicated, trusted directory."""
    root = Path(directory)
    if root.is_symlink() or any(parent.is_symlink() for parent in root.absolute().parents):
        raise ValueError("Artifact output must not traverse symlinks")
    if not isinstance(files, dict):
        raise ValueError("Expected a text file mapping")
    for relative, content in files.items():
        checked_relative(relative)
        if not isinstance(content, str):
            raise ValueError("Artifact file contents must be strings")
        target = root / relative
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError("Artifact output must not traverse symlinks")
        if target.exists() and not target.is_file():
            raise ValueError("Artifact output must be a regular file")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


@dataclass(frozen=True)
class WorkloadCase:
    case_id: str
    title: str
    objective: str
    public_files: dict[str, str]
    tasks: list[dict]
    reference_artifacts: dict[str, dict]
    grade_task: Callable[[str, dict], dict]
    assemble: Callable[[list[dict]], dict]
    grade_final: Callable[[dict], dict]

    def public_spec(self) -> dict:
        """No reference artifacts or private acceptance code in this contract."""
        return copy.deepcopy({"case_id": self.case_id, "title": self.title, "objective": self.objective,
                              "public_files": self.public_files, "tasks": self.tasks})

    def task(self, task_id: str) -> dict:
        for task in self.tasks:
            if task["task_id"] == task_id:
                return copy.deepcopy(task)
        raise ValueError("Unknown workload subtask: " + task_id)
