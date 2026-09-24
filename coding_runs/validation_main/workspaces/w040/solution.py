from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append an iterable of (key, value) string pairs to a URL's query.

    Existing query parameters keep their original order, duplicate keys and
    blank values. New pairs are appended in the order supplied, preserving
    duplicates and blanks as well. Standard URL form encoding is used.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
