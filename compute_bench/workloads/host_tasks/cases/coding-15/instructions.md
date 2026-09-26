Fix the bugs in this Python repository: Parse a quoted shell pipeline into structured commands.

Implement `parse_pipeline(text)`. Use shell-like quoting and comments to parse one pipeline into stages; split only unquoted pipes; collect leading NAME=value assignments into env with last value winning; require a nonempty argv in every stage; reject empty stages, invalid assignment names, and assignment tokens after argv; preserve quoted spaces and never execute commands. All validation failures must raise `ValueError`.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
