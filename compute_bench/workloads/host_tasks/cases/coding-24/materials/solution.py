"""Memoised computation with dependency-aware invalidation."""

from store import Store


class Cache:
    """Memoises ``compute`` results and invalidates dependent entries."""

    def __init__(self):
        self.store = Store()
        self.calls = 0

    def compute(self, key, sources=(), produce=None):
        """Return the cached value for *key*, computing it when necessary.

        *sources* lists the keys this value derives from.  When any source is
        invalidated, every value that transitively depends on it must be
        recomputed.  *produce* is a zero-argument callable returning the
        value.  A cached value is returned without calling *produce* again.
        """
        if self.store.has(key):
            return self.store.get(key)
        if produce is None:
            raise ValueError("produce is required when the value is not cached")
        self.calls += 1
        return self.store.put(key, produce(), sources)

    def invalidate(self, key):
        """Drop *key* and everything that depends on it, directly or not."""
        # BUG: only the named key is dropped.  Values that recorded it as a
        # source keep serving stale results.
        self.store.drop(key)
