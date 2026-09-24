from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append ``(key, value)`` pairs to a URL's existing query string.

    Existing pair order, repeated keys and blank values are preserved, and the
    supplied pairs are appended in order (duplicates and blanks included).
    URL form encoding (``quote_plus``) is applied to the whole query, so spaces,
    plus signs, ampersands and Unicode are encoded correctly.  The path and
    fragment are left untouched and relative URLs are supported.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
