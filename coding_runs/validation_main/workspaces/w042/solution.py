from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append an iterable of (key, value) string pairs to a URL's query.

    Existing pairs keep their order, duplicates and blank values; new pairs
    are appended in the supplied order, also preserving duplicates and blanks.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
