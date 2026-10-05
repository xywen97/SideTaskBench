"""Registration storage and MRO inspection for a small dispatch registry."""


def mro_chain(cls):
    """Return *cls* and its base classes in method-resolution order.

    ``object`` is excluded: it is a universal fallback, not a registrable
    target, so it never participates in specificity comparison.
    """
    return [base for base in cls.__mro__ if base is not object]


class Registry:
    """A mapping from class to handler, with no resolution policy of its own."""

    def __init__(self):
        self._handlers = {}

    def register(self, cls, handler):
        """Record *handler* for *cls*, replacing any previous registration."""
        self._handlers[cls] = handler

    def handlers(self):
        """Return a shallow copy of the class-to-handler mapping."""
        return dict(self._handlers)

    def registered(self, cls):
        """Return whether *cls* itself has a registered handler."""
        return cls in self._handlers
