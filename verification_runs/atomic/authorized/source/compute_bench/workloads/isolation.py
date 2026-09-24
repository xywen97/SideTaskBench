"""Execute a candidate bundle only through MicroCoder's existing Linux sandbox."""

from pathlib import Path
import tempfile

from microcoder.sandbox import Sandbox

from .contracts import write_files


def run_python(files: dict[str, str], command: str, timeout: float = 20) -> dict:
    with tempfile.TemporaryDirectory(prefix="workload-grade-") as temporary:
        workspace = Path(temporary)
        write_files(workspace, files)
        return Sandbox(workspace, allow_ipc=False).run(command, timeout=timeout)
