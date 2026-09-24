from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's query string.

    Existing query parameter order, duplicate keys and blank values are
    preserved; the supplied pairs are appended in order (duplicates and
    blanks included). Standard URL form encoding is applied and the URL
    path and fragment are left intact. Relative URLs are supported.
    """
    parts = urlsplit(url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    appended = [(str(key), str(value)) for key, value in pairs]
    query = urlencode(existing + appended)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, parts.fragment)
    )
