from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = OrderedDict()

    def get(self, key, default=None):
        # A hit must be distinguished from a stored falsey value, so use a
        # membership test rather than `self._items.get(key, default)`.
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        # A miss returns the default without inserting anything.
        return default

    def put(self, key, value):
        self._items[key] = value
        # Assigning to an existing key does not change its order, so refresh
        # recency explicitly for both inserts and replacements.
        self._items.move_to_end(key)
        # Evict only when capacity is exceeded (updates never add entries).
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self):
        return len(self._items)
