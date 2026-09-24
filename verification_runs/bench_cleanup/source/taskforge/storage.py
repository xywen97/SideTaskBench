"""Atomic local job files. One process owns a delivery session at a time."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile

from .models import identifier


class JobStore:
    def __init__(self, root: Path):
        original = Path(root).absolute()
        if original.is_symlink() or any(parent.is_symlink() for parent in original.parents):
            raise ValueError("Job storage must not traverse symlinks")
        self.root = original.resolve()

    def path(self, relative: str) -> Path:
        path = self.root / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Invalid storage path")
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != self.root.parent):
            raise ValueError("Storage paths must not traverse symlinks")
        return path

    def read(self, relative: str):
        return json.loads(self.path(relative).read_text(encoding="utf-8"))

    def write(self, relative: str, value) -> None:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as stream:
                name = stream.name
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
        finally:
            if name and Path(name).exists():
                Path(name).unlink()

    def assignments(self) -> list[dict]:
        directory = self.path("assignments")
        return [self.read("assignments/" + path.name) for path in sorted(directory.glob("*.json"))] if directory.exists() else []

    def assignment(self, assignment_id: str) -> dict:
        return self.read("assignments/" + identifier(assignment_id) + ".json")

    def save_assignment(self, value: dict) -> None:
        self.write("assignments/" + identifier(value["assignment_id"]) + ".json", value)

    @contextmanager
    def session_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with self.path("session.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("This job already has an active local delivery session") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
