from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = OrderedDict()

    def get(self, key, default=None):
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        return default

    def put(self, key, value):
        if key in self._items:
            self._items.move_to_end(key)
        self._items[key] = value
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self):
        return len(self._items)
