Fix the bugs in this Python repository: Build a deterministic and safe file copy manifest.

Implement `build_copy_plan(root, entries)`. Normalize POSIX and backslash separators, reject absolute paths and traversal, validate nonnegative sizes and 64-digit SHA-256 digests, normalize accepted digests to lowercase, reject normalized duplicates, preserve the input, and return records sorted by normalized path with targets rooted below root. All validation failures must raise `ValueError`.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
