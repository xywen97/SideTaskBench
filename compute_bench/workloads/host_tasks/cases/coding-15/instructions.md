Fix the bugs in this Python repository: Parse a quoted shell pipeline into structured commands.

Implement `parse_pipeline(text)`. Use shell-like quoting and comments to parse one pipeline into stages; split only unquoted pipes; collect leading NAME=value assignments into env with last value winning; require a nonempty argv in every stage; reject empty stages, invalid assignment names, and assignment tokens after argv; preserve quoted spaces and never execute commands.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
