"""Fetch pinned CPython documents and emit task.json for the multi-file host cases.

Materials (README, modules, tests, private solution and hidden tests) are authored
files on disk and are NOT touched here. This script owns only two things:

* the byte-exact upstream reference snapshots under ``reference/``, and
* the ``reference.documents`` provenance records in ``task.json``.

Every host task keeps a three-document collection so that the multi-file cohort
stays comparable with coding-21; document count is varied only by an explicit
opt-in in ``CASES``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "compute_bench/workloads/host_tasks/cases"

COMMIT = "cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69"
RAW = f"https://raw.githubusercontent.com/python/cpython/{COMMIT}/Doc/"
SOURCE = f"https://github.com/python/cpython/blob/{COMMIT}/Doc/"
VERSION = "Python 3.11.14"
RETRIEVED = "2026-09-25T09:00:05.862699+00:00"
LICENSE = "PSF license; documentation examples also under Zero-Clause BSD"

DOCS = {
    "string": ("library/string.rst", "Python string — Common string operations; template substitution"),
    "re": ("library/re.rst", "Python re — Regular expression operations"),
    "exceptions": ("library/exceptions.rst", "Python built-in exceptions"),
    "functools": ("library/functools.rst", "Python functools — Higher-order functions and operations on callable objects"),
    "abc": ("library/abc.rst", "Python abc — Abstract base classes"),
    "typing": ("library/typing.rst", "Python typing — Support for type hints"),
    "collections": ("library/collections.rst", "Python collections — Container datatypes"),
    "copy": ("library/copy.rst", "Python copy — Shallow and deep copy operations"),
    "json": ("library/json.rst", "Python json — JSON encoder and decoder"),
    "datetime": ("library/datetime.rst", "Python datetime — Basic date and time types"),
    "decimal": ("library/decimal.rst", "Python decimal — Decimal fixed point and floating point arithmetic"),
    "functions": ("library/functions.rst", "Python built-in functions"),
}

CASES_SPEC = {
    "coding-22": {
        "topic": "Python string Template substitution rules for $name, ${name} and escaped dollar signs",
        "context": ("Template rendering is checked against an independent scanner example that does not "
                    "change the template text under test."),
        "docs": ["string", "re", "exceptions"],
    },
    "coding-23": {
        "topic": "Python functools singledispatch specificity ordering for overlapping registrations",
        "context": ("Dispatch resolution is checked against an independent registration example that does "
                    "not change the provider registry under test."),
        "docs": ["functools", "abc", "typing"],
    },
    "coding-24": {
        "topic": "Python functools cache invalidation and collections state coherence",
        "context": ("Cache coherence is checked against an independent invalidation example that does not "
                    "change the store under test."),
        "docs": ["functools", "collections", "copy"],
    },
    "coding-25": {
        "topic": "Python json deserialisation, decimal quantisation and datetime parsing across a call chain",
        "context": ("The three-stage pipeline is checked against an independent end-to-end example that "
                    "does not change the record under test."),
        "docs": ["json", "decimal", "datetime", "re", "functions", "exceptions"],
    },
}


def fetch(relative: str) -> bytes:
    with urllib.request.urlopen(RAW + relative, timeout=45) as response:
        data = response.read()
    text = data.decode("utf-8")
    # Mirror the contract in tests/test_reference_collections.py rather than an
    # arbitrary byte floor: upstream docs must be prose, not a redirect or stub.
    if "<html" in text[:300].lower() or len(text.split()) < 250 or len(text.splitlines()) < 50:
        raise ValueError("Expected an upstream documentation source: " + relative)
    return data


def write_documents(case_id: str, spec: dict, fetched: dict) -> list[dict]:
    directory = CASES / case_id
    for stale in (directory / "reference").iterdir():
        if stale.name not in {"python-LICENSE.txt", "python-DOC-LICENSE.rst"}:
            stale.unlink()
    records = []
    for index, key in enumerate(spec["docs"], 1):
        relative, title = DOCS[key]
        data = fetched[relative]
        name = "reference.md" if index == 1 else f"{index:02d}-{Path(relative).name}"
        (directory / "reference" / name).write_bytes(data)
        text = data.decode()
        records.append({
            "path": f"reference/{name}",
            "workspace_path": "docs/reference.md" if index == 1 else f"docs/references/{name}",
            "title": title, "source_url": SOURCE + relative, "download_url": RAW + relative,
            "upstream_repository": "python/cpython", "upstream_commit": COMMIT,
            "version": VERSION, "format": "rst", "retrieved_at": RETRIEVED,
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "lines": len(text.splitlines()), "words": len(text.split()),
            "license": LICENSE, "license_path": "reference/python-LICENSE.txt",
            "license_url": f"https://github.com/python/cpython/blob/{COMMIT}/LICENSE",
            "transform": "none; full upstream source, original bytes",
        })
    return records


def main() -> None:
    keys = {DOCS[key][0] for spec in CASES_SPEC.values() for key in spec["docs"]}
    fetched = {relative: fetch(relative) for relative in sorted(keys)}
    for case_id, spec in CASES_SPEC.items():
        directory = CASES / case_id
        metadata = json.loads((directory / "task.json").read_text(encoding="utf-8"))
        records = write_documents(case_id, spec, fetched)
        metadata["reference"] = {"topic": spec["topic"], "path": records[0]["path"],
                                 "compatibility_context": spec["context"], "documents": records}
        (directory / "task.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
        print(case_id, [(record["workspace_path"], record["lines"]) for record in records])


if __name__ == "__main__":
    main()
