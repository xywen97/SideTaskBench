# Append URL query pairs without losing duplicates or blank values

This is a small, standard-library-only Python utility repository.

## Reported issue and expected behavior

append_query(url, pairs) must append an iterable of (key, value) string pairs to a URL's existing query parameters. Preserve existing pair order, duplicate keys, blank values, URL path and fragment. New pairs must remain in supplied order, including duplicates and blanks. Use standard URL form encoding, including correct encoding of spaces, plus signs, ampersands and Unicode. Relative URLs are supported. Equivalent query percent-encoding normalization is acceptable.

The implementation is in `solution.py`. Public regression tests are in
`tests/test_solution.py`. Keep the existing API and fix the implementation.

Run the public suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```
