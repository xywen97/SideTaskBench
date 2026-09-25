# Bound retries by total attempts and preserve exception behavior

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

retry_call(operation, attempts=3, retry_on=(Exception,)) calls a zero-argument operation and returns its first successful result. attempts means the maximum total number of calls, not the number of retries after an initial call. It must be a positive integer excluding bool; invalid values raise ValueError before calling operation. Retry only exceptions matching retry_on. Propagate other exceptions immediately and re-raise the final matching exception if all attempts fail. Preserve the original exception instance. Do not add sleeps.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

External reference documents may be found with the reference search tool.
The repository and this issue contain all requirements needed for the repair.
