from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's query string.

    Existing query parameters keep their original order, duplicate keys and
    blank values. New pairs are appended in the supplied order, preserving
    duplicates and blanks as well. Path and fragment are left untouched.
    """
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
