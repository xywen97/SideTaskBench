Fix the bugs in this Python repository: Validate an archive extraction plan before writing files.

Implement `plan_archive(members, max_total)`. Each member has exactly the fields name/size/is_dir. Normalize slash separators; reject absolute and traversal paths, duplicates, descendants below files, and file/directory conflicts. Sizes and `max_total` are nonnegative non-boolean integers, `is_dir` is boolean, and directories have size zero. Enforce the total file-size limit, preserve input, and return normalized members with directories before descendants in deterministic path order. All validation failures must raise `ValueError`.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
