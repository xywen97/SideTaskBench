Fix the bugs in this Python repository: Build a deterministic and safe file copy manifest.

Implement `build_copy_plan(root, entries)`. Normalize POSIX and backslash separators, reject absolute paths and traversal, validate nonnegative sizes and 64-digit SHA-256 digests, reject normalized duplicates, preserve the input, and return records sorted by normalized path with targets rooted below root.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
