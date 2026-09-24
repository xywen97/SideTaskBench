from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    parts = urlsplit(url)
    # parse_qsl returns ordered (key, value) pairs and, with
    # keep_blank_values=True, retains entries such as ``empty=``.
    query = parse_qsl(parts.query, keep_blank_values=True)
    # Extend the list (rather than a dict) so repeated keys and the
    # supplied order are preserved for both existing and new pairs.
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
