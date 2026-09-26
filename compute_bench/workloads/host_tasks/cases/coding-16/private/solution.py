import re
from email.utils import getaddresses

_LOCAL=re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_DOMAIN=re.compile(r'^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*$')

def normalize_mailboxes(values):
    raw=list(values)
    if any(not isinstance(v,str) or '\r' in v or '\n' in v for v in raw): raise ValueError('invalid input')
    parsed=getaddresses(raw); result=[]; positions={}
    if not parsed: return []
    for name,address in parsed:
        name=' '.join(name.split()); address=address.strip()
        if address.count('@') != 1: raise ValueError('invalid address')
        local,domain=address.rsplit('@',1)
        if _LOCAL.fullmatch(local) is None or _DOMAIN.fullmatch(domain) is None: raise ValueError('invalid address')
        normalized=local + '@' + domain.lower(); key=normalized.casefold()
        if key in positions:
            if name and not result[positions[key]]['name']: result[positions[key]]['name']=name
            continue
        positions[key]=len(result); result.append({'name':name,'address':normalized})
    return result
