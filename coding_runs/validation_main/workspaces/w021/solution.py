from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append ``(key, value)`` pairs to a URL's existing query parameters.

    Existing pairs are preserved in order, including duplicate keys and
    blank values.  New pairs are appended in the order supplied, again
    preserving duplicates and blanks.  Standard form encoding is applied
    to the whole query component.  Works for absolute and relative URLs.
    """
    parts = urlsplit(url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    new_pairs = list(pairs)
    query = urlencode(existing + new_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
