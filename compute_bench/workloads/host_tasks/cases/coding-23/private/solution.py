"""Resolve a handler for a class using the registry's specificity policy."""

from dispatch import Registry, mro_chain

__all__ = ["Registry", "register", "resolve"]


def register(registry, cls, handler):
    """Register *handler* for *cls*."""
    registry.register(cls, handler)


def resolve(registry, cls):
    """Return the handler registered for the most specific class of *cls*.

    Specificity follows *cls*'s method-resolution order: a handler registered
    for ``cls`` itself wins over one registered for a base class, and among
    base classes the nearest ancestor wins.  Registration order must not
    affect the result.  Raises ``LookupError`` when nothing in the chain is
    registered.
    """
    available = registry.handlers()
    for klass in mro_chain(cls):
        if klass in available:
            return available[klass]
    raise LookupError(cls)
