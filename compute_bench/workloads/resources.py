"""Read declarative task assets as data, never as importable modules."""

import json
from pathlib import Path, PurePosixPath


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(char) < 32 for char in value)
            or PurePosixPath(value).is_absolute()
            or any(part in {"", ".", ".."} or part.startswith(".") for part in value.split("/"))):
        raise ValueError("Material paths must be safe relative POSIX paths")
    return value


def read_bytes(root: Path, relative: str) -> bytes:
    path = Path(root) / relative_path(relative)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.absolute().parents):
        raise ValueError("Material paths must not traverse symlinks")
    if not path.is_file():
        raise ValueError(f"Material is not a regular file: {path}")
    return path.read_bytes()


def read_text(root: Path, relative: str) -> str:
    return read_bytes(root, relative).decode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate material JSON key: " + key)
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Non-finite JSON value: " + value)


def read_json(root: Path, relative: str):
    return json.loads(read_text(root, relative), object_pairs_hook=_unique_object,
                      parse_constant=_nonfinite)


def inventory(root: Path) -> dict[str, bytes]:
    """Return exact resource bytes; interpreter caches are not task assets."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Material root must be a regular directory")
    result = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError("Material inventory cannot contain symlinks")
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        result[relative] = read_bytes(root, relative)
    return result
