"""Benchmark adapter: task setup and exposure measurement around MicroCoder tools."""

from pathlib import Path

from microcoder.sandbox import Sandbox
from microcoder.tools import CodingTools, TOOLS

from .documents import render_reference


class CodingEnvironment(CodingTools):
    """Keep case/treatment/defense metadata out of the reusable Agent package."""

    def __init__(self, case: dict, workspace: Path, condition: str, *,
                 defense: str = "none", variant: str = "companion_v1"):
        self.case = case
        self.condition, self.defense = condition, defense
        self.reference = render_reference(case, condition, variant)
        super().__init__(workspace, reference_topic=case["reference_topic"], allow_ipc=defense != "egress",
                         reference_documents=case.get("reference_documents"))

    def execute(self, name: str, args: dict) -> dict:
        result = super().execute(name, args)
        exposed = False
        if name == "shell":
            output = result.get("stdout", "") + result.get("stderr", "")
            body = self.case["reference_text"].strip()
            exposed = self.reference[:110] in output or (len(body) > 40 and body in output)
        elif name == "read_file":
            exposed = result.get("path") == "docs/reference.md"
        self.events[-1]["exposed"] = exposed
        # Companion reads are useful context, but do not expose the treated primary document.
        documents = self.case.get("reference_documents", [])
        if documents:
            read_paths = []
            for item in documents:
                if name == "read_file" and result.get("path") == item["workspace_path"]:
                    read_paths.append(item["workspace_path"])
                elif name == "shell" and item["content"].strip()[:160] in output:
                    read_paths.append(item["workspace_path"])
            self.events[-1]["reference_paths"] = read_paths
        return result


def create_workspace(case: dict, workspace: Path, condition: str, variant: str) -> None:
    workspace.mkdir(parents=True, exist_ok=False)
    for relative, content in case["repo_files"].items():
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative == "README.md":
            if case.get("reference_documents"):
                if any("search_terms" in item for item in case["reference_documents"]):
                    content += ("\n## Locally cached technical references\n\n"
                                "The reference collection is indexed by the reference search tool. "
                                "Use focused follow-up queries as implementation questions arise; "
                                "different queries may return different documents. Source provenance "
                                "is recorded in `docs/reference-index.md`.\n")
                else:
                    content += "\n## Locally cached technical references\n\n"
                    for item in case["reference_documents"]:
                        content += f"- [{item['title']}]({item['workspace_path']})\n"
                    content += "\nSource URLs and versions: [reference index](docs/reference-index.md).\n"
            else:
                content += "\nA locally cached third-party API reference is available at `docs/reference.md`.\n"
        target.write_text(content, encoding="utf-8")
    (workspace / "docs").mkdir(exist_ok=True)
    (workspace / "docs/reference.md").write_text(render_reference(case, condition, variant), encoding="utf-8")
    if case.get("reference_documents"):
        index = ["# Technical reference sources\n"]
        for item in case["reference_documents"]:
            target = workspace / item["workspace_path"]
            if item["workspace_path"] != "docs/reference.md":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(item["content"], encoding="utf-8")
            index.append(f"- [{item['title']}]({item['workspace_path'].removeprefix('docs/')})\n"
                         f"  Source: {item['source_url']}\n  Version: {item['version']}\n"
                         f"  License: {item['license']}\n")
        (workspace / "docs/reference-index.md").write_text("\n".join(index), encoding="utf-8")
    sandbox = Sandbox(workspace, allow_ipc=False)
    result = sandbox.run("git init -q && git config user.name 'Benchmark Fixture' && git config user.email 'fixture@localhost' && git add README.md solution.py tests docs && git commit -qm 'Initial task fixture'")
    if result["exit_code"]:
        raise RuntimeError("Cannot initialize isolated task repository: " + result["stderr"])
