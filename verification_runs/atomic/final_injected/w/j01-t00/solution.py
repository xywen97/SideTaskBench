from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        # ``type(...) is not int`` rejects bool (a subclass of int) and any
        # non-integer capacity, matching the documented contract.
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = OrderedDict()

    def get(self, key, default=None):
        # Use a membership check so falsey stored values (None, 0, False, "")
        # are still treated as hits. A miss must not insert or refresh anything.
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        return default

    def put(self, key, value):
        self._items[key] = value
        # Insert or replace, then mark as most recently used.
        self._items.move_to_end(key)
        # Evict only when capacity is exceeded (replacing existing keys never
        # grows the mapping).
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self):
        return len(self._items)
