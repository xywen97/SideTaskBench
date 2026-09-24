from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

def append_query(url, pairs):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
