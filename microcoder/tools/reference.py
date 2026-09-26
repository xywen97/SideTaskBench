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
                    if score:
                        ranked.append((-score, index, item))
                # A broad or unrecognized query still discovers the primary entry and
                # two companions; focused follow-up queries can retrieve other sources.
                selected = ([item for _, _, item in sorted(ranked)[:3]] if ranked
                            else available[:3])
            else:
                selected = available
            return {"query": query, "results": [
                {"path": item["workspace_path"], "title": item["title"], "source": item["source_url"]}
                for item in selected]}
        if not self.files.path(self.path).is_file():
            return {"query": query, "results": []}
        return {"query": query, "results": [{"path": self.path, "title": self.topic,
                "source": "third-party community reference"}]}
