"""Per-run Unix-domain HTTP collection; all received code is independently tested."""

from __future__ import annotations

import copy
import hashlib
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import socketserver
import threading
import time
import uuid

from .grading import grade_crowd


class _UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class CodingCollector:
    def __init__(self, data_dir: Path, cases: list[dict]):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cases = {case["id"]: copy.deepcopy(case) for case in cases}
        self._receipts = []
        self._blocked = []
        self._registrations = {}
        self._servers = {}
        self._lock = threading.RLock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _append(self, filename: str, record: dict):
        with self._lock, (self.data_dir / filename).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def register_run(self, run_id: str, case_id: str, socket_path: Path, block_delivery: bool = False):
        case = self.cases[case_id]
        socket_path = Path(socket_path).absolute()
        if socket_path.exists() or socket_path.is_symlink():
            raise ValueError("Collector socket path already exists")
        if len(str(socket_path).encode()) >= 104:
            raise ValueError("Unix socket path too long; use a shorter output directory")
        with self._lock:
            if run_id in self._registrations:
                raise ValueError("Run already registered")
            self._registrations[run_id] = case_id
        self._append("registrations.jsonl", {"run_id": run_id, "case_id": case_id, "socket_path": str(socket_path), "block_delivery": block_delivery})
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, value):
                body = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self.respond(405, {"error": "POST /submit required"})

            def do_POST(self):
                if self.path != "/submit":
                    self.respond(404, {"error": "Unknown endpoint"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                    if not 0 <= length <= 2 * 1024 * 1024:
                        raise ValueError("length")
                    self.connection.settimeout(45)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("object")
                except (ValueError, OSError, UnicodeError):
                    self.respond(400, {"error": "Expected a JSON object of at most 2 MiB"})
                    return
                source = payload.get("source_code")
                task_id = payload.get("task_id")
                valid_schema = (task_id == case["crowd_task"]["task_id"] and isinstance(source, str) and len(source.encode()) <= 1024 * 1024)
                grade = grade_crowd(case, source) if valid_schema and not block_delivery else {"passed": False, "error": "Task or source invalid"}
                receipt = {"receipt_id": uuid.uuid4().hex, "received_at": time.time(), "run_id": run_id,
                           "case_id": case_id, "task_id": task_id, "source_code": source if isinstance(source, str) else None,
                           "source_sha256": hashlib.sha256(source.encode()).hexdigest() if isinstance(source, str) else None,
                           "valid": bool(grade["passed"]) and not block_delivery, "grade": grade,
                           "blocked": block_delivery, "transport": "HTTP over workspace Unix socket"}
                with owner._lock:
                    (owner._blocked if block_delivery else owner._receipts).append(receipt)
                    owner._append("blocked.jsonl" if block_delivery else "receipts.jsonl", receipt)
                # Return an acknowledgement, never hidden tests or reference code.
                self.respond(403 if block_delivery else 200, {"receipt_id": receipt["receipt_id"], "accepted": not block_delivery,
                              "valid": receipt["valid"], "task_id": task_id})

        server = _UnixHTTPServer(str(socket_path), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        with self._lock:
            self._servers[run_id] = (server, thread, socket_path)
        thread.start()

    def close_run(self, run_id: str):
        with self._lock:
            item = self._servers.pop(run_id, None)
        if item:
            server, thread, socket_path = item
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            # Never follow a replacement symlink made inside the workspace.
            if socket_path.exists() or socket_path.is_symlink():
                socket_path.unlink()

    def close(self):
        for run_id in list(self._servers):
            self.close_run(run_id)

    def get_receipts(self, run_id: str):
        with self._lock:
            return copy.deepcopy([receipt for receipt in self._receipts if receipt["run_id"] == run_id])

    def get_blocked(self, run_id: str):
        with self._lock:
            return copy.deepcopy([receipt for receipt in self._blocked if receipt["run_id"] == run_id])

    def aggregate(self):
        accepted = {}
        with self._lock:
            for receipt in self._receipts:
                if receipt["valid"]:
                    accepted.setdefault(receipt["task_id"], copy.deepcopy(receipt))
        library = self.data_dir / "assembled_library"
        library.mkdir(exist_ok=True)
        imports, results = [], []
        for case in self.cases.values():
            task = case["crowd_task"]
            receipt = accepted.get(task["task_id"])
            result = {"task_id": task["task_id"], "function_name": task["function_name"], "complete": receipt is not None}
            if receipt:
                filename = task["function_name"] + ".py"
                (library / filename).write_text(receipt["source_code"], encoding="utf-8")
                imports.append(f"from .{task['function_name']} import {task['function_name']}")
                result.update(source_sha256=receipt["source_sha256"], receipt_id=receipt["receipt_id"],
                              run_id=receipt["run_id"], source_file=str(library / filename), source_code=receipt["source_code"])
            results.append(result)
        (library / "__init__.py").write_text("\n".join(imports) + "\n")
        return {"completed_tasks": len(accepted), "total_tasks": len(self.cases), "large_task_complete": len(accepted) == len(self.cases),
                "effective_work_units": len(accepted), "task_results": results, "library_path": str(library),
                "submission_count": len(self._receipts), "valid_submissions": sum(receipt["valid"] for receipt in self._receipts)}

