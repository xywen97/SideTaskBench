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
            words = set(re.findall(r"[a-z0-9_]+", query.casefold()))
            ranked = []
            for index, item in enumerate(available):
                title_words = set(re.findall(r"[a-z0-9_]+", item["title"].casefold()))
                content_words = set(re.findall(r"[a-z0-9_]+", item["content"].casefold()))
                score = 3 * len(words & title_words) + len(words & content_words)
                ranked.append((-score, index, item))
            # Every host task uses the same retrieval policy. Prefer relevant documents
            # not yet returned in this run, then fill from the remaining collection.
            unseen = [row for row in ranked if row[2]["workspace_path"] not in self.returned_paths]
            seen = [row for row in ranked if row[2]["workspace_path"] in self.returned_paths]
            selected = [item for _, _, item in sorted(unseen) + sorted(seen)][:3]
            self.returned_paths.update(item["workspace_path"] for item in selected)
            return {"query": query, "results": [
                {"path": item["workspace_path"], "title": item["title"], "source": item["source_url"]}
                for item in selected]}
        if not self.files.path(self.path).is_file():
            return {"query": query, "results": []}
        return {"query": query, "results": [{"path": self.path, "title": self.topic,
                "source": "third-party community reference"}]}
