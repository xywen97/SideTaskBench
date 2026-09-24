"""Additional source evidence for explicitly invoked document-v1 experiments."""

from __future__ import annotations

import hashlib
from pathlib import Path

from compute_bench.coding.provenance import snapshot_sources as snapshot_mainline_sources


IDENTITY = {"name": "Document v1 archive", "package": "legacy.document_v1",
            "entrypoint": "legacy.document_v1.cli:main"}
REQUIRED_SOURCES = frozenset({"__init__.py"} | {
    "document_v1/" + name + ".py" for name in (
        "__init__", "__main__", "agent", "audit", "cli", "collector", "environment",
        "experiment", "provenance", "report", "scenarios", "scoring",
    )
})
_OLD_DOCUMENT_SOURCES = {"agent.py", "environment.py", "experiment.py", "scenarios.py", "scoring.py"}


def snapshot_sources(output_dir: Path) -> dict:
    """Retain the shared runtime plus the actual archived experiment sources.

    Coding's default snapshot remains independent of this archive. The extra
    package and metadata are added only by explicit document-v1 experiments.
    """
    archive = Path(__file__).resolve().parent
    package = archive.parent
    files = {}
    for source in [package / "__init__.py", *sorted(archive.rglob("*.py"))]:
        if source.is_symlink() or not source.resolve().is_relative_to(package):
            raise ValueError("Legacy snapshot cannot follow package symlinks")
        files[source.relative_to(package).as_posix()] = source.read_bytes()
    if not REQUIRED_SOURCES.issubset(files):
        raise ValueError("Document-v1 archive source package is incomplete")
    metadata = snapshot_mainline_sources(output_dir)
    destination = Path(output_dir).resolve() / "source/legacy"
    hashes = {}
    for relative, content in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        hashes[relative] = hashlib.sha256(content).hexdigest()
    metadata.update(experiment_family="document_v1", legacy_source_root="source/legacy",
                    legacy_source_sha256=hashes, legacy_identity=dict(IDENTITY))
    return metadata


def inspect_legacy_snapshot(output_dir: Path, metadata: dict) -> dict:
    """Verify the archive without executing snapshots; accept historical runs."""
    root = Path(output_dir).resolve()
    package = root / "source/legacy"
    fields = {"legacy_source_root", "legacy_source_sha256", "legacy_identity"}
    benchmark = root / "source/compute_bench"
    archived_execution = benchmark.exists() and not _OLD_DOCUMENT_SOURCES.issubset(
        path.relative_to(benchmark).as_posix() for path in benchmark.rglob("*.py"))
    required = (metadata.get("experiment_family") == "document_v1" or package.exists()
                or bool(fields.intersection(metadata)) or archived_execution)
    if not required:
        return {"required": False, "checks": []}
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": "legacy_" + name, "passed": bool(passed),
                       **({"detail": detail} if detail else {})})

    check("provenance_present", fields.issubset(metadata) and metadata.get("experiment_family") == "document_v1")
    check("identity", metadata.get("legacy_identity") == IDENTITY)
    check("source_root", metadata.get("legacy_source_root") == "source/legacy")
    hashes = metadata.get("legacy_source_sha256", {})
    if not isinstance(hashes, dict):
        hashes = {}
    actual = ({path.relative_to(package).as_posix(): path for path in package.rglob("*.py")}
              if package.is_dir() and not package.is_symlink() else {})
    check("source_inventory", bool(hashes) and set(actual) == set(hashes) and REQUIRED_SOURCES.issubset(hashes))
    for relative, expected in hashes.items():
        if not isinstance(relative, str):
            check("source_path", False, "Source keys must be relative filenames")
            continue
        target = package / relative
        safe = (not Path(relative).is_absolute() and ".." not in Path(relative).parts
                and not target.is_symlink() and target.resolve().is_relative_to(package.resolve())
                and target.resolve().is_relative_to(root))
        check("source_path/" + relative, safe)
        if safe:
            check("source_hash/" + relative,
                  target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected)
    return {"required": True, "checks": checks}
