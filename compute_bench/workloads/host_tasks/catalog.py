"""Load host task manifests and separate public/private material files."""

from pathlib import Path

from ..resources import read_json, read_text, relative_path


CASE_ROOT = Path(__file__).with_name("cases")


def _manifest(case_id: str, root: Path) -> dict:
    if relative_path(case_id) != Path(case_id).name:
        raise ValueError("Host case ID must be a single directory name")
    metadata = read_json(root, case_id + "/task.json")
    if metadata.get("schema_version") != 1 or metadata.get("id") != case_id:
        raise ValueError("Host task identity or schema mismatch")
    if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        raise ValueError("Host task title is required")
    return metadata


def _material(root: Path, path: str, prefix: str) -> str:
    relative_path(path)
    if not path.startswith(prefix + "/"):
        raise ValueError(f"Material must belong to {prefix}/")
    return read_text(root, path)


def load_host_tasks(case_root: Path | None = None) -> list[dict]:
    root = CASE_ROOT if case_root is None else Path(case_root)
    index = read_json(root, "catalog.json")
    ids = index.get("case_ids")
    if (index.get("schema_version") != 1 or not isinstance(ids, list)
            or len(ids) < 8 or any(not isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("Host catalog requires at least eight unique case IDs")
    cases = []
    for case_id in ids:
        metadata = _manifest(case_id, root)
        directory = root / case_id
        public, private = metadata["repo_files"], metadata["reference_files"]
        solution_file = metadata.get("solution_file", "solution.py")
        if (not isinstance(public, dict) or not isinstance(private, dict)
                or not {"README.md", solution_file, "tests/test_solution.py"} <= public.keys()
                or set(private) != {solution_file}):
            raise ValueError("Host task must declare repair files and independent reference")
        for destination in public:
            relative_path(destination)
            if destination.split("/")[0] in {"private", "reference", "docs"}:
                raise ValueError("Reserved host workspace material destination")
        reference = metadata["reference"]
        if not isinstance(reference.get("topic"), str) or not isinstance(reference.get("compatibility_context"), str):
            raise ValueError("Host reference metadata must be text")
        if metadata["user_task"] != "instructions.md":
            raise ValueError("Host instructions must be instructions.md")
        cases.append({
            "id": case_id, "title": metadata["title"],
            "solution_file": solution_file,
            "user_task": read_text(directory, metadata["user_task"]).rstrip("\n"),
            "repo_files": {path: _material(directory, source, "materials") for path, source in public.items()},
            "hidden_tests": _material(directory, metadata["hidden_tests"], "private"),
            "reference_files": {path: _material(directory, source, "private") for path, source in private.items()},
            "reference_topic": reference["topic"],
            "reference_text": _material(directory, reference["path"], "reference"),
        })
        if "documents" in reference:
            documents = reference["documents"]
            if not isinstance(documents, list) or not 3 <= len(documents) <= 6:
                raise ValueError("Host reference collection requires 3–6 documents")
            paths = [item["workspace_path"] for item in documents]
            if (len(paths) != len(set(paths)) or paths[0] != "docs/reference.md"
                    or documents[0]["path"] != reference["path"]):
                raise ValueError("Reference collection must have one primary document and unique paths")
            loaded = []
            for item in documents:
                destination = relative_path(item["workspace_path"])
                if destination != "docs/reference.md" and not destination.startswith("docs/references/"):
                    raise ValueError("Reference documents must belong to docs/references/")
                loaded.append({**item, "content": _material(directory, item["path"], "reference")})
            cases[-1]["reference_documents"] = loaded
    return cases


def compatibility_context(case_id: str) -> str:
    return _manifest(case_id, CASE_ROOT)["reference"]["compatibility_context"]
