from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _iter_pairs(pairs):
    """Yield (key, value) pairs, accepting a mapping or any iterable of pairs."""
    items = getattr(pairs, "items", None)
    if callable(items):
        return list(items())
    return list(pairs)


def append_query(url, pairs):
    """Append ``pairs`` to ``url``'s existing query parameters.

    Existing parameters keep their order, duplicate keys and blank values;
    the new pairs are appended afterwards in the order supplied. Standard
    application/x-www-form-urlencoded encoding is used for the whole query.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(_iter_pairs(pairs))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
