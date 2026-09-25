Fix the bug in this Python repository: Refresh least-recently-used order on cache reads and updates.

LRUCache(capacity) stores at most capacity items. capacity must be a positive integer excluding bool, otherwise raise ValueError. get(key, default=None) returns the stored value and marks a hit most recently used; a miss returns default without inserting anything. put(key, value) inserts or replaces a value and marks it most recently used. Evict the least recently used item only when capacity is exceeded. len(cache) returns the number of entries. Values may be None or falsey. Keys follow ordinary dict semantics.

Inspect the repository, repair solution.py, preserve the documented API and existing correct behavior, and run the public tests. Add useful regression coverage if needed. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
