"""A fixed local reference index; remote fetching is deliberately absent."""

from pathlib import Path
import re

from .files import FileTools


class ReferenceTool:
    """Advertise the existing local reference file; never fetch remote content."""

    def __init__(self, workspace: Path, reference_topic: str = "Local technical reference",
                 reference_path: str = "docs/reference.md", documents: list[dict] | None = None):
        self.files = FileTools(workspace)
        self.topic = reference_topic
        self.path = reference_path
        self.documents = documents
        self.returned_paths: set[str] = set()

    def search(self, query: str) -> dict:
        if self.documents is not None:
            available = [item for item in self.documents
                         if self.files.path(item["workspace_path"]).is_file()]
            if any("search_terms" in item for item in available):
                words = set(re.findall(r"[a-z0-9_]+", query.casefold()))
                ranked = []
                for index, item in enumerate(available):
                    terms = {term.casefold() for term in item.get("search_terms", [])}
                    title_words = set(re.findall(r"[a-z0-9_]+", item["title"].casefold()))
                    score = 3 * len(words & terms) + len(words & title_words)
                    ranked.append((-score, index, item))
                # Prefer relevant documents that this run has not seen yet, then fill
                # from the remaining unseen collection. Repeated focused queries thus
                # retain query relevance while eventually exposing the whole fixed set.
                unseen = [row for row in ranked if row[2]["workspace_path"] not in self.returned_paths]
                seen = [row for row in ranked if row[2]["workspace_path"] in self.returned_paths]
                selected = [item for _, _, item in sorted(unseen) + sorted(seen)][:3]
            else:
                selected = available
            self.returned_paths.update(item["workspace_path"] for item in selected)
            return {"query": query, "results": [
                {"path": item["workspace_path"], "title": item["title"], "source": item["source_url"]}
                for item in selected]}
        if not self.files.path(self.path).is_file():
            return {"query": query, "results": []}
        return {"query": query, "results": [{"path": self.path, "title": self.topic,
                "source": "third-party community reference"}]}
