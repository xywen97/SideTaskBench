"""Store and collect lightweight marks on Python objects."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Mark:
    name: str
    args: tuple = field(default_factory=tuple)
    kwargs: tuple[tuple[str, object], ...] = field(default_factory=tuple)


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _mark_owners(obj, consider_mro):
    if not isinstance(obj, type):
        return ()
    if consider_mro:
        return obj.__bases__
    return (obj,)


def get_unpacked_marks(obj, *, consider_mro=True):
    """Return marks stored on *obj*."""
    owners = _mark_owners(obj, consider_mro)
    if owners:
        marks = _as_list(obj.__dict__.get("pytestmark"))
        for owner in owners:
            marks.extend(_as_list(getattr(owner, "pytestmark", None)))
        return marks
    return _as_list(getattr(obj, "pytestmark", None))


def store_mark(obj, mark):
    """Append *mark* directly to *obj* without changing a base class."""
    marks = get_unpacked_marks(obj)
    marks.append(mark)
    obj.pytestmark = marks
