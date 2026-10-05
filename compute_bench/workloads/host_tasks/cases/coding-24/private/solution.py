"""Memoised computation with dependency-aware invalidation."""

from store import Store


class Cache:
    """Memoises ``compute`` results and invalidates dependent entries."""

    def __init__(self):
        self.store = Store()
        self.calls = 0

    def compute(self, key, sources=(), produce=None):
        """Return the cached value for *key*, computing it when necessary."""
        if self.store.has(key):
            return self.store.get(key)
        if produce is None:
            raise ValueError("produce is required when the value is not cached")
        self.calls += 1
        return self.store.put(key, produce(), sources)

    def invalidate(self, key):
        """Drop *key* and everything that depends on it, directly or not."""
        pending = [key]
        seen = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(self.store.dependents(current))
            self.store.drop(current)
