# Third-party technical reference: Python OrderedDict LRU cache move_to_end get update eviction

Source: a community-maintained reference excerpt.

OrderedDict and LRU cache reference

An OrderedDict records insertion order. Assigning a new value to
an existing key does not automatically mark it as the most recent
key. move_to_end(key) moves an existing item to the newest end.
popitem(last=False) removes the oldest item. An LRU policy treats
successful reads and writes as accesses; a cache miss does not
count as an inserted value.

A stored None, zero, False, or empty string is still a cache hit.
A membership check distinguishes an absent key from these values.
Updating an existing item should not consume extra capacity.

