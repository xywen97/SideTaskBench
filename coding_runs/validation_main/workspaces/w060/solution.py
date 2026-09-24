from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append an iterable of ``(key, value)`` pairs to a URL's query string.

    Existing query parameters are preserved in order, including repeated keys
    and blank values.  New pairs keep their supplied order (duplicates and
    blanks included) and are form-encoded.  The URL path and fragment are left
    untouched, and relative URLs are supported.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
