from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        # bool is a subclass of int, so compare the exact type to reject it.
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = OrderedDict()

    def get(self, key, default=None):
        # A membership check keeps falsey stored values (None, 0, False, "")
        # distinguishable from an absent key.
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        return default

    def put(self, key, value):
        # Assigning an existing key does not move it in an OrderedDict, so
        # explicitly mark the write as the most recent access.
        self._items[key] = value
        self._items.move_to_end(key)
        # Updating an existing key never grows the cache; only evict when a
        # genuinely new entry pushes the size past capacity.
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self):
        return len(self._items)
