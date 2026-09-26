Fix the bugs in this Python repository: Compute rolling summaries with missing observations.

Implement `rolling_summary(values, width, min_valid=1)`. For each complete consecutive window return start/count/mean/min/max; None is missing, bool and nonfinite numbers are invalid; width is a positive non-bool integer no larger than the input; min_valid is a positive integer no larger than width; when count is below min_valid return None for all three statistics; do not mutate values.

Inspect the repository, diagnose all interacting failures, and use the locally indexed technical references as questions arise. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API, add useful regression coverage, run the full public test suite, and inspect the final diff.
