Fix the bug in this Python repository: invalidation must propagate through the dependency graph.

solution.Cache memoises computed values. compute(key, sources=(), produce=None) returns the cached value for key, calling produce only when the value is absent, and records that key derives from the names in sources. invalidate(key) must drop key and every value that depends on it, directly or transitively, so that a later compute for a dependent entry recomputes instead of serving a stale result. Keys that do not appear in any dependency edge are unaffected. Cache.calls counts the number of times produce ran.

The repository is split into two modules: store.py holds the values and the dependency edges, solution.py implements the cache and its invalidation policy. The bug is in solution.py.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
