# Traverse cursor pages through empty results without looping

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

fetch_all(fetch_page, start_cursor) calls fetch_page(cursor), which returns a dictionary with items:list and next_cursor:string-or-None. Preserve all items in page order, continue through empty pages, and stop only at a None cursor. A repeated cursor must raise ValueError before another fetch. A None start returns [] without calling fetch_page. Keep the public API unchanged.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```
