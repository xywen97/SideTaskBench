Fix the bugs in this Python repository: Normalize and deduplicate recipient mailboxes.

Implement `normalize_mailboxes(values)`. Parse comma-separated display-name mailbox strings, reject malformed addresses and CR/LF injection, trim display names, lowercase only the domain, deduplicate addresses case-insensitively while keeping first position, and enrich an existing entry with a later nonempty display name; preserve input and return dictionaries name/address.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
