from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's existing query parameters.

    Existing pairs keep their original order, duplicate keys and blank
    values.  The new ``pairs`` are appended afterwards in the order
    supplied, also preserving duplicates and blank values.  The URL path
    and fragment are left untouched.  Standard form encoding is applied.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
