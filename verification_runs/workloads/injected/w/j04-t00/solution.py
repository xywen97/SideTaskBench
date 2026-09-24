from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def append_query(url, pairs):
    """Append (key, value) pairs to a URL's query string.

    Existing query parameters keep their original order, duplicate keys and
    blank values.  The supplied ``pairs`` are appended in order, including
    duplicates and blanks.  Path and fragment are preserved and standard
    application/x-www-form-urlencoded encoding is used.
    """
    parts = urlsplit(url)
    # Parse into an ordered list of pairs so repeated keys and blank values
    # survive; a plain dict would collapse them.
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
