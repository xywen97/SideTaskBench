from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's query string.

    Existing query pairs keep their original order, duplicate keys and blank
    values.  The supplied ``pairs`` are appended afterwards in their given
    order, again preserving duplicates and blanks.  Standard URL form encoding
    is used for the rebuilt query component.
    """
    parts = urlsplit(url)

    # ``parse_qsl`` returns an ordered sequence of pairs, unlike ``dict`` which
    # would silently drop duplicate keys.  ``keep_blank_values`` is required so
    # that entries such as ``empty=`` survive parsing.
    query = parse_qsl(parts.query, keep_blank_values=True)

    # Accept either an iterable of (key, value) pairs or a mapping.  Materialize
    # so one-shot iterables/generators are consumed exactly once.
    if hasattr(pairs, "items"):
        pairs = pairs.items()
    query.extend(pairs)

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
