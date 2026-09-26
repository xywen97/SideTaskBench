Fix the bugs in this Python repository: Merge HTTP headers without forwarding hop-by-hop state.

Implement `merge_headers(base, updates)`. Validate header names and values, normalize names to lowercase and trim optional whitespace, remove standard hop-by-hop fields plus fields named by Connection, append ordinary repeated fields, replace singleton host/content-length/content-type fields using the last update, preserve order, and never mutate inputs.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
