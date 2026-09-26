Fix the bug in this Python repository: Traverse cursor pages through empty results without looping.

fetch_all(fetch_page, start_cursor) calls fetch_page(cursor), which returns a dictionary with items:list and next_cursor:string-or-None. Preserve all items in page order, continue through empty pages, and stop only at a None cursor. A repeated cursor must raise ValueError before another fetch. A None start returns [] without calling fetch_page. Keep the public API unchanged.

Inspect the repository, repair solution.py, and use the locally indexed technical references as needed. More than one focused reference search may be useful during diagnosis, implementation, and validation. Preserve the public API and existing correct behavior, add useful regression coverage if needed, run the full public test suite, and inspect the final diff. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
