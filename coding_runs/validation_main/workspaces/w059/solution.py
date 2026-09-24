from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append ``(key, value)`` pairs to a URL's query string.

    Existing query parameters are preserved in order, including duplicate
    keys and blank values. The supplied pairs are appended in order, also
    keeping duplicates and blanks. Standard URL form encoding is applied.
    """
    parts = urlsplit(url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    query = urlencode(existing + list(pairs))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, parts.fragment)
    )
