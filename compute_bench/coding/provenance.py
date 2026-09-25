"""Source snapshots for the benchmark, coding Agent, and third-party platform."""

from __future__ import annotations

import hashlib
import importlib.util
import ast
from pathlib import Path


SOURCE_LAYOUT_VERSION = 4
SUPPORTED_SOURCE_LAYOUTS = frozenset({1, 2, 3, 4})

LEGACY_REQUIRED_BENCHMARK_SOURCES = frozenset({
    "coding/tasks.py", "coding/runner.py", "coding/grading.py", "coding/environment.py",
    "coding/sandbox.py", "agent.py", "llm.py",
})

REQUIRED_BENCHMARK_SOURCES = frozenset({
    "__init__.py", "__main__.py", "cli.py", "io.py",
    "coding/__init__.py", "coding/__main__.py", "coding/cli.py", "coding/tasks.py",
    "coding/runner.py", "coding/grading.py", "coding/environment.py", "coding/documents.py",
    "coding/platform.py", "coding/provenance.py", "coding/audit.py", "coding/report.py", "coding/rescore.py",
    "workloads/isolation.py", "workloads/provider_atomic/__init__.py",
    "workloads/provider_atomic/catalog.py", "workloads/provider_atomic/python_grading.py",
})


def required_benchmark_sources(layout: int) -> frozenset[str]:
    """Version the benchmark contract without requiring removed import shims."""
    if type(layout) is not int or layout not in SUPPORTED_SOURCE_LAYOUTS:
        raise ValueError("Unsupported source snapshot layout")
    return REQUIRED_BENCHMARK_SOURCES if layout == 4 else LEGACY_REQUIRED_BENCHMARK_SOURCES


AGENT_IDENTITY = {
    "name": "MicroCoder",
    "package": "microcoder",
    "entrypoint": "microcoder.core.agent:run_agent",
    "prompt_source": "prompts/coding.py",
    "tools_source": "tools/registry.py",
    "sandbox_source": "sandbox/linux.py",
}

REQUIRED_AGENT_SOURCES = frozenset({
    "__init__.py", "config.py", "llm.py", "core/__init__.py", "core/agent.py", "core/trace.py",
    "prompts/__init__.py", "prompts/coding.py", "tools/__init__.py", "tools/registry.py",
    "tools/files.py", "tools/shell.py", "tools/reference.py", "sandbox/__init__.py", "sandbox/linux.py",
})

PLATFORM_IDENTITY = {
    "name": "TaskForge",
    "package": "taskforge",
    "entrypoint": "taskforge.platform:TaskForge",
    "reference_source": "distribution/reference.py",
    "collection_source": "collection.py",
    "assembly_source": "assembly.py",
    "planning_source": "planning.py",
}

REQUIRED_PLATFORM_SOURCES = frozenset({
    "__init__.py", "__main__.py", "models.py", "planning.py", "platform.py",
    "storage.py", "cli.py", "collection.py", "assembly.py",
    "distribution/__init__.py", "distribution/reference.py",
})


def _package_root(package: str) -> Path:
    # Finding a top-level module spec does not execute its __init__.py.
    spec = importlib.util.find_spec(package)
    if spec is None or spec.origin is None or spec.submodule_search_locations is None:
        raise RuntimeError(f"The {package} package is required for source snapshots")
    return Path(spec.origin).resolve().parent


def _agent_package_root() -> Path:
    return _package_root("microcoder")


def _platform_package_root() -> Path:
    return _package_root("taskforge")


def snapshot_sources(output_dir: Path) -> dict:
    """Copy complete Python sources and return manifest provenance fields.

    output_dir is a fresh run root or its recovery_N root. Existing source files
    are never overwritten, so a recovery cannot silently replace prior evidence.
    Files are read once, and the same bytes are hashed and written. Environment
    files, caches and runtime outputs are excluded from all package snapshots.
    """
    output_dir = Path(output_dir).resolve()
    package_roots = {
        "compute_bench": Path(__file__).resolve().parents[1],
        "microcoder": _agent_package_root(),
        "taskforge": _platform_package_root(),
    }
    source_root = output_dir / "source"
    if source_root.is_symlink() or (source_root.exists() and any(source_root.iterdir())):
        raise ValueError("Source snapshot destination must be empty")
    sources = {}
    for package, root in package_roots.items():
        files = {}
        for path in sorted(root.rglob("*.py")):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Source snapshot cannot follow a package symlink")
            relative = path.relative_to(root).as_posix()
            files[relative] = path.read_bytes()
        if not files or "__init__.py" not in files:
            raise ValueError(f"Missing Python package sources: {package}")
        sources[package] = files
    for package, required in (("compute_bench", REQUIRED_BENCHMARK_SOURCES),
                              ("microcoder", REQUIRED_AGENT_SOURCES), ("taskforge", REQUIRED_PLATFORM_SOURCES)):
        if not required.issubset(sources[package]):
            missing = sorted(required - sources[package].keys())
            raise ValueError(f"{package} source snapshot is incomplete: " + ", ".join(missing))
    hashes = {}
    for package, files in sources.items():
        hashes[package] = {}
        for relative, content in files.items():
            target = source_root / package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Refuse races or accidental snapshot reuse as well as old files.
            with target.open("xb") as stream:
                stream.write(content)
            hashes[package][relative] = hashlib.sha256(content).hexdigest()
    return {
        "source_layout_version": SOURCE_LAYOUT_VERSION,
        "source_sha256": hashes["compute_bench"],
        "agent_source_sha256": hashes["microcoder"],
        "agent_source_root": "source/microcoder",
        "agent_identity": dict(AGENT_IDENTITY),
        "platform_source_sha256": hashes["taskforge"],
        "platform_source_root": "source/taskforge",
        "platform_identity": dict(PLATFORM_IDENTITY),
    }


def _imports_package(source: str, package: str) -> bool:
    for node in ast.walk(ast.parse(source)):
        names = ([item.name for item in node.names] if isinstance(node, ast.Import)
                 else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
        if any(name == package or name.startswith(package + ".") for name in names):
            return True
    return False


def _inspect_package_snapshot(output_dir, metadata, *, label, package, identity, required_sources, layouts):
    root = Path(output_dir).resolve()
    benchmark = root / "source/compute_bench"
    package_dir = root / "source" / package
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), **({"detail": detail} if detail else {})})

    layout = metadata.get("source_layout_version", 1)
    check(label + "_source_layout_version", type(layout) is int and layout in SUPPORTED_SOURCE_LAYOUTS)
    imports_package = False
    for path in benchmark.rglob("*.py"):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            check(label + "_dependency_source_paths", False, str(path.relative_to(root)))
            continue
        try:
            imports_package |= _imports_package(path.read_text(encoding="utf-8"), package)
        except (SyntaxError, UnicodeError):
            check(label + "_dependency_source_syntax", False, str(path.relative_to(root)))
    fields = {label + "_source_sha256", label + "_source_root", label + "_identity"}
    required = imports_package or package_dir.exists() or bool(fields.intersection(metadata)) or metadata.get("source_layout_version") in layouts
    if not required:
        return {"required": False, "checks": checks}
    check(label + "_provenance_present", fields.issubset(metadata) and metadata.get("source_layout_version") in layouts)
    check(label + "_identity", metadata.get(label + "_identity") == identity)
    check(label + "_source_root", metadata.get(label + "_source_root") == "source/" + package)
    hashes = metadata.get(label + "_source_sha256", {})
    if not isinstance(hashes, dict):
        hashes = {}
    actual = {path.relative_to(package_dir).as_posix(): path for path in package_dir.rglob("*.py")} if package_dir.is_dir() and not package_dir.is_symlink() else {}
    check(label + "_source_inventory", bool(hashes) and set(actual) == set(hashes)
          and required_sources.issubset(hashes))
    for relative, expected in hashes.items():
        path = package_dir / relative
        safe = (not Path(relative).is_absolute() and ".." not in Path(relative).parts
                and not path.is_symlink() and path.resolve().is_relative_to(package_dir.resolve())
                and path.resolve().is_relative_to(root))
        check(label + "_source_path/" + relative, safe)
        if not safe:
            continue
        check(label + "_source_hash/" + relative, path.is_file() and
              hashlib.sha256(path.read_bytes()).hexdigest() == expected)
    return {"required": True, "checks": checks}


def inspect_agent_snapshot(output_dir: Path, metadata: dict) -> dict:
    """Verify MicroCoder for layouts 2-4; retain combined-package evidence."""
    return _inspect_package_snapshot(output_dir, metadata, label="agent", package="microcoder",
                                     identity=AGENT_IDENTITY, required_sources=REQUIRED_AGENT_SOURCES, layouts={2, 3, 4})


def inspect_platform_snapshot(output_dir: Path, metadata: dict) -> dict:
    """Verify TaskForge for layouts 3/4 without importing retained platform code.

    Platform imports, a platform source directory, or any platform metadata make
    the complete provenance mandatory even if the layout version is removed.
    """
    return _inspect_package_snapshot(output_dir, metadata, label="platform", package="taskforge",
                                     identity=PLATFORM_IDENTITY, required_sources=REQUIRED_PLATFORM_SOURCES, layouts={3, 4})
