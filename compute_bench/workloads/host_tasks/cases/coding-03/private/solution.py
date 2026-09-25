from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

def append_query(url, pairs):
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
