"""Source snapshots for the benchmark, coding Agent, and third-party platform."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from compute_bench.workloads.resources import inventory


SOURCE_LAYOUT_VERSION = 6
REQUIRED_BENCHMARK_SOURCES = frozenset({
    "__init__.py", "__main__.py", "cli.py", "io.py",
    "coding/__init__.py", "coding/__main__.py", "coding/cli.py", "coding/tasks.py",
    "coding/pairing.py",
    "coding/runner.py", "coding/grading.py", "coding/environment.py", "coding/documents.py",
    "coding/platform.py", "coding/provenance.py", "coding/audit.py", "coding/report.py", "coding/rescore.py",
    "workloads/python_grading.py", "workloads/provider_atomic/__init__.py",
    "workloads/provider_atomic/catalog.py",
    "workloads/resources.py", "workloads/host_tasks/__init__.py",
    "workloads/host_tasks/catalog.py",
})

MATERIAL_ROOTS = (
    "workloads/host_tasks/cases",
    "workloads/provider_atomic/cases",
    "workloads/provider_atomic/private",
)


def task_materials() -> dict[str, bytes]:
    root = Path(__file__).resolve().parents[1]
    return {prefix + "/" + path: data for prefix in MATERIAL_ROOTS
            for path, data in inventory(root / prefix).items()}


def material_hashes() -> dict[str, str]:
    return {path: hashlib.sha256(data).hexdigest() for path, data in task_materials().items()}


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
    """Snapshot runtime sources and exact task materials separately.

    output_dir is a fresh run root or its recovery_N root. Existing source files
    are never overwritten, so a recovery cannot silently replace prior evidence.
    Source/material bytes are hashed and copied without importing fixtures. Environment
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
            if package == "compute_bench" and any(relative.startswith(prefix + "/") for prefix in MATERIAL_ROOTS):
                continue
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
    resources = task_materials()
    for relative, content in resources.items():
        target = output_dir / "task_materials" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
    return {
        "source_layout_version": SOURCE_LAYOUT_VERSION,
        "task_material_sha256": {path: hashlib.sha256(data).hexdigest() for path, data in resources.items()},
        "source_sha256": hashes["compute_bench"],
        "agent_source_sha256": hashes["microcoder"],
        "agent_source_root": "source/microcoder",
        "agent_identity": dict(AGENT_IDENTITY),
        "platform_source_sha256": hashes["taskforge"],
        "platform_source_root": "source/taskforge",
        "platform_identity": dict(PLATFORM_IDENTITY),
    }
