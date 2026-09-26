Fix the bugs in this Python repository: Resolve layered typed configuration without mutating inputs.

Implement `resolve_settings(layers)`. Apply layers in order over fixed defaults timeout=5.0, retries=3, enabled=True, tags=[]; parse strict strings and native values; None resets a key to its default; tags accept a comma string or iterable, trim and deduplicate in order; reject unknown keys, bool-as-number, nonfinite timeout, and invalid values; return fresh data without mutation.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
