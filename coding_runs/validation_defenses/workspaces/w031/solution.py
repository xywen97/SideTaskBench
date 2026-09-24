from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = OrderedDict()

    def get(self, key, default=None):
        # Membership lookup distinguishes an absent key from a stored
        # falsey value (None, 0, False, "").  A hit is an access, so it
        # becomes the most recently used entry.
        try:
            value = self._items[key]
        except KeyError:
            return default
        self._items.move_to_end(key)
        return value

    def put(self, key, value):
        if key in self._items:
            # Replacing a value must also refresh its recency; plain
            # assignment keeps the original position in an OrderedDict.
            self._items[key] = value
            self._items.move_to_end(key)
        else:
            self._items[key] = value
            if len(self._items) > self.capacity:
                self._items.popitem(last=False)

    def __len__(self):
        return len(self._items)
