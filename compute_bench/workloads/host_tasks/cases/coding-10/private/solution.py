import re

_TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_HOP = {'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade'}
_SINGLE = {'host','content-length','content-type'}

def merge_headers(base, updates):
    pairs = []
    for name, value in list(base) + list(updates):
        if not isinstance(name, str) or _TOKEN.fullmatch(name) is None or not isinstance(value, str) or '\r' in value or '\n' in value:
            raise ValueError('invalid header')
        pairs.append((name.lower(), value.strip(' \t')))
    hop = set(_HOP)
    for name, value in pairs:
        if name == 'connection':
            hop.update(part.strip().lower() for part in value.split(',') if part.strip())
    result = [(n, v) for n, v in pairs[:len(base)] if n not in hop]
    for name, value in pairs[len(base):]:
        if name in hop:
            continue
        if name in _SINGLE:
            result = [(n, v) for n, v in result if n != name]
        result.append((name, value))
    return result
