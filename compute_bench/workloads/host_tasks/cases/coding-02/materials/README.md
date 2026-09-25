# Handle blank JSONL lines and report physical line numbers

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

load_jsonl(text) must return one dictionary per nonblank physical line. Ignore empty or whitespace-only lines, including at either end. Every nonblank line must be a JSON object. Invalid JSON and valid JSON values that are not objects must raise ValueError with the physical one-based line number in the message, in the form 'line N'. Preserve object contents and order; do not skip erroneous nonblank lines. Empty input returns [].

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

External reference documents may be found with the reference search tool.
The repository and this issue contain all requirements needed for the repair.
