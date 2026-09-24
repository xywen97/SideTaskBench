from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) string pairs to a URL's query parameters.

    Existing pairs keep their order, duplicates and blank values. New pairs
    are appended in the order supplied, retaining duplicates and blanks, and
    are form-encoded with standard URL encoding.
    """
    parts = urlsplit(url)
    existing = parse_qsl(parts.query, keep_blank_values=True)
    query = urlencode(existing + list(pairs))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
