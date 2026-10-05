Fix the bug in this Python repository: render templates with correct placeholder handling.

solution.substitute(text, mapping, safe=False) replaces every placeholder in a template string using a value mapping. Support `$name` and `${name}` placeholders, and treat `$$` as a literal dollar sign. `str()` is applied to each substituted value. When a placeholder has no value, raise `MissingPlaceholder` unless `safe` is true, in which case the original placeholder spelling is preserved verbatim. Any other dollar sequence - for example a lone `$`, a `$` followed by a digit, or an empty `${}` - must raise `ValueError`. The mapping must never be mutated.

The repository is split into two modules: tokens.py performs the scanning, solution.py renders the result. The bug is in solution.py.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
