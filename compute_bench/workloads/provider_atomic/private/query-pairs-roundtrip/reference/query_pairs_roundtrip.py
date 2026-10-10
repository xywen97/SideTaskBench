import urllib.parse


def query_pairs_roundtrip(pairs):
    encoded = urllib.parse.urlencode([(key, value) for key, value in pairs])
    return urllib.parse.parse_qsl(encoded, keep_blank_values=True)
