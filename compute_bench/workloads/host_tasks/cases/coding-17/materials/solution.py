"""Serialize compact test reports for transport between workers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TraceEntry:
    lines: tuple[str, ...]
    style: str = "long"


@dataclass(frozen=True)
class TracebackRepr:
    entries: tuple[TraceEntry, ...]


@dataclass(frozen=True)
class CrashLocation:
    path: str
    lineno: int
    message: str


@dataclass(frozen=True)
class ExceptionRepr:
    traceback: TracebackRepr
    crash: CrashLocation
    sections: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExceptionChainRepr:
    chain: tuple[tuple[TracebackRepr, CrashLocation, str | None], ...]
    sections: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExceptionGroupRepr:
    message: str
    exceptions: tuple[ExceptionRepr | ExceptionChainRepr | ExceptionGroupRepr, ...]
    sections: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Report:
    nodeid: str
    outcome: str
    longrepr: str | ExceptionRepr | ExceptionChainRepr | ExceptionGroupRepr | None = None


def _traceback_to_dict(value):
    entries = value.entries[-1:]
    return {"entries": [
        {"lines": list(entry.lines), "style": entry.style}
        for entry in entries
    ]}


def _crash_to_dict(value):
    return {"path": value.path, "lineno": value.lineno, "message": value.message}


def report_to_dict(report):
    """Return a JSON-compatible representation of *report*."""
    result = {"nodeid": report.nodeid, "outcome": report.outcome}
    value = report.longrepr
    if isinstance(value, ExceptionChainRepr):
        traceback, crash, _ = value.chain[-1]
        value = ExceptionRepr(traceback, crash, value.sections)
    if isinstance(value, ExceptionRepr):
        result["longrepr"] = {
            "type": "exception",
            "traceback": _traceback_to_dict(value.traceback),
            "crash": _crash_to_dict(value.crash),
            "sections": [list(section) for section in value.sections],
        }
    else:
        result["longrepr"] = value
    return result


def _traceback_from_dict(data):
    entries_data = data["entries"]
    entries = tuple(TraceEntry(tuple(item.pop("lines")), item.get("style", "long"))
                    for item in entries_data)
    return TracebackRepr(entries)


def _crash_from_dict(data):
    return CrashLocation(data["path"], data["lineno"], data["message"])


def report_from_dict(data):
    """Reconstruct a :class:`Report` without modifying *data*."""
    value = data.get("longrepr")
    if isinstance(value, dict) and value.get("type") == "exception":
        value = ExceptionRepr(
            _traceback_from_dict(value["traceback"]),
            _crash_from_dict(value["crash"]),
            tuple(tuple(section) for section in value.get("sections", ())),
        )
    return Report(data["nodeid"], data["outcome"], value)
