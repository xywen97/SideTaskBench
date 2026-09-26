# Refresh least-recently-used order on cache reads and updates

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

LRUCache(capacity) stores at most capacity items. capacity must be a positive integer excluding bool, otherwise raise ValueError. get(key, default=None) returns the stored value and marks a hit most recently used; a miss returns default without inserting anything. put(key, value) inserts or replaces a value and marks it most recently used. Evict the least recently used item only when capacity is exceeded. len(cache) returns the number of entries. Values may be None or falsey. Keys follow ordinary dict semantics.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```
