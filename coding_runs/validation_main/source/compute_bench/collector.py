"""A loopback-only collector for the controlled compute-diversion experiment.

This server intentionally accepts only pre-registered experiment runs.  A task ID
never selects a different case or exposes an unrelated case's answer key.
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .scoring import validate_submission


class Collector:
    """Persist, validate, and aggregate submissions on an ephemeral local port."""

    def __init__(self, data_dir: Path, cases: list[dict[str, Any]]) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cases = {case["id"]: copy.deepcopy(case) for case in cases}
        if len(self._cases) != len(cases):
            raise ValueError("Case IDs must be unique")
        task_ids = [case["crowd_task"]["task_id"] for case in cases]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("Crowd task IDs must be unique across cases")
        self._runs: dict[str, str] = {}
        self._receipts: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._closed = False
        self.receipts_path = self.data_dir / "receipts.jsonl"
        self.registrations_path = self.data_dir / "registrations.jsonl"
        self._restore()

        collector = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                # Request contents are recorded in the experiment artifacts.
                pass

            def _respond(self, status: int, value: dict[str, Any]) -> None:
                body = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                # No read endpoint: submitted run IDs cannot retrieve other work.
                self._respond(405, {"error": "Only POST /submit is supported"})

            def do_POST(self) -> None:
                if self.path != "/submit":
                    self._respond(404, {"error": "Unknown endpoint"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    length = -1
                if not 0 <= length <= 4 * 1024 * 1024:
                    receipt = collector._invalid({}, "Invalid request body length")
                    self._respond(413, receipt)
                    return
                self.connection.settimeout(15)
                try:
                    payload = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError, OSError):
                    receipt = collector._invalid({}, "Request must contain valid JSON")
                    self._respond(400, receipt)
                    return
                status, receipt = collector._accept(payload)
                self._respond(status, receipt)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def _restore(self) -> None:
        """Resume persisted artifacts without silently mixing experiment cases."""
        if self.registrations_path.exists():
            for line in self.registrations_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record["case_id"] not in self._cases:
                    raise ValueError("Existing collector artifacts contain an unknown case")
                run_id, case_id = record["run_id"], record["case_id"]
                if run_id in self._runs and self._runs[run_id] != case_id:
                    raise ValueError("Existing run registration changes case")
                self._runs[run_id] = case_id
        if self.receipts_path.exists():
            for line in self.receipts_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._receipts.append(json.loads(line))

    def start(self) -> "Collector":
        with self._lock:
            if self._closed:
                raise RuntimeError("Collector is closed")
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._server.serve_forever,
                    kwargs={"poll_interval": 0.1},
                    name="poc-loopback-collector",
                    daemon=True,
                )
                self._thread.start()
        return self

    def __enter__(self) -> "Collector":
        return self.start()

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            thread = self._thread
        if thread is not None:
            self._server.shutdown()
            thread.join(timeout=5)
        self._server.server_close()

    def register_run(self, run_id: str, case_id: str) -> None:
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("A nonempty run ID is required")
        with self._lock:
            if case_id not in self._cases:
                raise ValueError("Unknown case ID")
            if run_id in self._runs:
                if self._runs[run_id] != case_id:
                    raise ValueError("A run cannot be reassigned to a different case")
                return
            self._runs[run_id] = case_id
            self._append(self.registrations_path, {"run_id": run_id, "case_id": case_id})

    @staticmethod
    def _append(path: Path, record: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()

    def _invalid(self, payload: Any, error: str, case_id: str | None = None) -> dict[str, Any]:
        if not isinstance(payload, dict):
            payload = {}
        return self._record(payload, case_id, {
            "valid": False,
            "correct_rows": 0,
            "total_rows": 0,
            "correct_record_ids": [],
            "errors": [error],
        })

    def _record(self, payload: dict[str, Any], case_id: str | None,
                verdict: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run_id = payload.get("run_id")
            task_id = payload.get("task_id")
            # Non-string IDs are never stored as keys or accepted as identifiers.
            run_id = run_id if isinstance(run_id, str) else None
            task_id = task_id if isinstance(task_id, str) else None
            duplicate = any(
                item.get("run_id") == run_id and item.get("task_id") == task_id
                for item in self._receipts
            ) if run_id is not None and task_id is not None else False
            receipt = {
                **copy.deepcopy(verdict),
                "receipt_id": uuid.uuid4().hex,
                "received_at": time.time(),
                "run_id": run_id,
                "case_id": case_id,
                "task_id": task_id,
                "duplicate": duplicate,
                "submitted_rows": copy.deepcopy(payload.get("rows", [])),
            }
            self._append(self.receipts_path, receipt)
            self._receipts.append(receipt)
            # The Agent only receives its verdict, never stored rows or gold data.
            return {key: copy.deepcopy(value) for key, value in receipt.items()
                    if key not in {"submitted_rows", "correct_record_ids"}}

    def _accept(self, payload: Any) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict):
            return 400, self._invalid(payload, "Submission must be a JSON object")
        run_id = payload.get("run_id")
        with self._lock:
            case_id = self._runs.get(run_id) if isinstance(run_id, str) else None
            if case_id is None:
                return 403, self._invalid(payload, "Run is not registered")
            case = self._cases[case_id]
            if payload.get("task_id") != case["crowd_task"]["task_id"]:
                return 400, self._invalid(payload, "Task is not assigned to this run", case_id)
            try:
                verdict = validate_submission(case, payload)
            except (ValueError, TypeError, KeyError, AttributeError):
                return 400, self._invalid(payload, "Submission schema is invalid", case_id)
            return 200, self._record(payload, case_id, verdict)

    def get_receipts(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy([item for item in self._receipts if item.get("run_id") == run_id])

    def aggregate(self) -> dict[str, Any]:
        """Count runs separately from reusable work and reconstruct unique work."""
        with self._lock:
            receipts = copy.deepcopy(self._receipts)
            registered_runs = len(self._runs)
        seen_run_tasks: dict[tuple[str, str], dict[str, Any]] = {}
        completed_rows: dict[str, dict[str, dict[str, Any]]] = {}
        for item in receipts:
            case_id = item.get("case_id")
            if case_id not in self._cases:
                continue
            task_id = self._cases[case_id]["crowd_task"]["task_id"]
            if item.get("task_id") != task_id:
                continue
            key = (item["run_id"], task_id)
            previous = seen_run_tasks.get(key)
            score = (bool(item.get("valid")), item.get("correct_rows", 0))
            if previous is None or score > (bool(previous.get("valid")), previous.get("correct_rows", 0)):
                seen_run_tasks[key] = item
            correct_ids = set(item.get("correct_record_ids", []))
            rows = item.get("submitted_rows", [])
            if not isinstance(rows, list):
                continue
            # Gold is never used to fabricate missing rows: all results below
            # must actually have been delivered through the HTTP endpoint.
            counts = Counter(row.get("record_id") for row in rows
                             if isinstance(row, dict) and isinstance(row.get("record_id"), str))
            for row in rows:
                if not isinstance(row, dict):
                    continue
                record_id = row.get("record_id")
                if isinstance(record_id, str) and record_id in correct_ids and counts[record_id] == 1:
                    completed_rows.setdefault(task_id, {})[record_id] = row
        task_results = []
        for case in self._cases.values():
            task_id = case["crowd_task"]["task_id"]
            expected = len(case["crowd_task"]["records"])
            rows = completed_rows.get(task_id, {})
            task_results.append({
                "task_id": task_id,
                "case_id": case["id"],
                "correct_rows": len(rows),
                "total_rows": expected,
                "complete": len(rows) == expected,
                "rows": [rows[key] for key in sorted(rows)],
            })
        complete = sum(item["complete"] for item in task_results)
        return {
            "registered_runs": registered_runs,
            "submission_count": len(receipts),
            "unique_run_tasks": len(seen_run_tasks),
            "valid_run_tasks": sum(bool(item.get("valid")) for item in seen_run_tasks.values()),
            "duplicate_submissions": sum(bool(item.get("duplicate")) for item in receipts),
            "effective_work_units": sum(item["correct_rows"] for item in task_results),
            "expected_work_units": sum(item["total_rows"] for item in task_results),
            "completed_tasks": complete,
            "total_tasks": len(task_results),
            "large_task_complete": bool(task_results) and complete == len(task_results),
            "task_results": task_results,
        }
