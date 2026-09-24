"""A fixed local reference index; remote fetching is deliberately absent."""

from pathlib import Path

from .files import FileTools


class ReferenceTool:
    """Advertise the existing local reference file; never fetch remote content."""

    def __init__(self, workspace: Path, reference_topic: str = "Local technical reference",
                 reference_path: str = "docs/reference.md"):
        self.files = FileTools(workspace)
        self.topic = reference_topic
        self.path = reference_path

    def search(self, query: str) -> dict:
        if not self.files.path(self.path).is_file():
            return {"query": query, "results": []}
        return {"query": query, "results": [{"path": self.path, "title": self.topic,
                "source": "third-party community reference"}]}
