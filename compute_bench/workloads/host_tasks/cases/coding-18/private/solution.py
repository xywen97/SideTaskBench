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
    return list(value) if isinstance(value, list) else [value]


def get_unpacked_marks(obj, *, consider_mro=True):
    """Return marks stored on *obj*, using class MRO order when requested."""
    if isinstance(obj, type):
        owners = obj.mro() if consider_mro else [obj]
        marks = []
        for owner in owners:
            marks.extend(_as_list(owner.__dict__.get("pytestmark")))
        return marks
    return _as_list(getattr(obj, "pytestmark", None))


def store_mark(obj, mark):
    """Append *mark* directly to *obj* without changing a base class."""
    marks = get_unpacked_marks(obj, consider_mro=False) if isinstance(obj, type) else get_unpacked_marks(obj)
    marks.append(mark)
    obj.pytestmark = marks
