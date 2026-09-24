from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    parts = urlsplit(url)

    # parse_qsl keeps pair order and repeated keys; keep_blank_values
    # preserves parameters whose value is empty (e.g. "empty=").
    query = parse_qsl(parts.query, keep_blank_values=True)

    # Extend (rather than dict.update) so new pairs keep their order and
    # any duplicate keys/blanks supplied by the caller are preserved.
    query.extend(pairs)

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
