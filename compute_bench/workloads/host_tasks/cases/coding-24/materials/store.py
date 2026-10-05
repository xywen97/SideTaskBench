"""Storage for memoised values and the dependencies recorded between them."""


class Store:
    """Holds cached values plus the reverse edges used for invalidation."""

    def __init__(self):
        self._values = {}
        self._sources = {}
        self._dependents = {}

    def get(self, key):
        """Return the cached value for *key*, or ``None`` when absent."""
        return self._values.get(key)

    def has(self, key):
        """Return whether *key* currently has a cached value."""
        return key in self._values

    def put(self, key, value, sources):
        """Cache *value* under *key*, recording the source keys it derives from.

        Raises ``KeyError`` when *key* is itself listed in *sources*, since a
        value may not depend on itself.
        """
        sources = tuple(sources)
        if key in sources:
            raise KeyError("value cannot depend on itself: " + repr(key))
        self.drop(key)
        self._values[key] = value
        self._sources[key] = set(sources)
        for source in sources:
            self._dependents.setdefault(source, set()).add(key)
        return value

    def drop(self, key):
        """Remove *key* and every dependency edge that points at it."""
        self._values.pop(key, None)
        for source in self._sources.pop(key, set()):
            dependents = self._dependents.get(source)
            if dependents is not None:
                dependents.discard(key)
                if not dependents:
                    del self._dependents[source]
        self._dependents.pop(key, None)

    def dependents(self, key):
        """Return the keys that recorded *key* as a source."""
        return set(self._dependents.get(key, ()))

    def keys(self):
        """Return the set of currently cached keys."""
        return set(self._values)
