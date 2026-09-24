from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's query string.

    Existing query pairs are preserved in order, including duplicates and
    blank values, followed by ``pairs`` in the order supplied (also keeping
    duplicates and blanks).  Path, scheme, netloc and fragment are kept.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
