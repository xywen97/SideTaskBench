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
    return {"entries": [
        {"lines": list(entry.lines), "style": entry.style}
        for entry in value.entries
    ]}


def _crash_to_dict(value):
    return {"path": value.path, "lineno": value.lineno, "message": value.message}


def _repr_to_dict(value):
    if isinstance(value, ExceptionChainRepr):
        return {
            "type": "chain",
            "chain": [
                {
                    "traceback": _traceback_to_dict(traceback),
                    "crash": _crash_to_dict(crash),
                    "description": description,
                }
                for traceback, crash, description in value.chain
            ],
            "sections": [list(section) for section in value.sections],
        }
    if isinstance(value, ExceptionRepr):
        return {
            "type": "exception",
            "traceback": _traceback_to_dict(value.traceback),
            "crash": _crash_to_dict(value.crash),
            "sections": [list(section) for section in value.sections],
        }
    if isinstance(value, ExceptionGroupRepr):
        return {
            "type": "group",
            "message": value.message,
            "exceptions": [_repr_to_dict(item) for item in value.exceptions],
            "sections": [list(section) for section in value.sections],
        }
    raise ValueError("unsupported longrepr value")


def report_to_dict(report):
    """Return a JSON-compatible representation of *report*."""
    value = report.longrepr
    if isinstance(value, (ExceptionRepr, ExceptionChainRepr, ExceptionGroupRepr)):
        value = _repr_to_dict(value)
    return {"nodeid": report.nodeid, "outcome": report.outcome, "longrepr": value}


def _traceback_from_dict(data):
    entries = tuple(TraceEntry(tuple(item["lines"]), item.get("style", "long"))
                    for item in data["entries"])
    return TracebackRepr(entries)


def _crash_from_dict(data):
    return CrashLocation(data["path"], data["lineno"], data["message"])


def _repr_from_dict(value):
    kind = value.get("type")
    sections = tuple(tuple(section) for section in value.get("sections", ()))
    if kind == "exception":
        return ExceptionRepr(
            _traceback_from_dict(value["traceback"]),
            _crash_from_dict(value["crash"]),
            sections,
        )
    if kind == "chain":
        chain = tuple(
            (
                _traceback_from_dict(item["traceback"]),
                _crash_from_dict(item["crash"]),
                item.get("description"),
            )
            for item in value["chain"]
        )
        return ExceptionChainRepr(chain, sections)
    if kind == "group":
        children = value.get("exceptions")
        if not isinstance(children, list):
            raise ValueError("group exceptions must be a list")
        return ExceptionGroupRepr(
            value["message"],
            tuple(_repr_from_dict(item) for item in children),
            sections,
        )
    raise ValueError("unknown longrepr type")


def report_from_dict(data):
    """Reconstruct a :class:`Report` without modifying *data*."""
    value = data.get("longrepr")
    if isinstance(value, dict):
        value = _repr_from_dict(value)
    return Report(data["nodeid"], data["outcome"], value)
