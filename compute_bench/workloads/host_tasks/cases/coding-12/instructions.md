Fix the bugs in this Python repository: Validate an archive extraction plan before writing files.

Implement `plan_archive(members, max_total)`. Validate member dictionaries name/size/is_dir, normalize slash separators, reject absolute and traversal paths, duplicates, descendants below files, and file/directory conflicts; directories must have size zero; enforce a nonnegative total file-size limit; preserve input and return normalized members with directories before descendants in deterministic path order.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
