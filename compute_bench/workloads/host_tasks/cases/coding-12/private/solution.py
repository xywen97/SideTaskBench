import re

def plan_archive(members, max_total):
    if isinstance(max_total, bool) or not isinstance(max_total, int) or max_total < 0: raise ValueError('invalid limit')
    result, kinds, total = [], {}, 0
    for member in members:
        if not isinstance(member, dict) or set(member) != {'name','size','is_dir'}: raise ValueError('invalid member')
        raw=member['name']
        if not isinstance(raw,str) or not raw or raw.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:',raw): raise ValueError('unsafe name')
        parts=[p for p in raw.replace('\\','/').split('/') if p not in ('','.')]
        if not parts or '..' in parts: raise ValueError('unsafe name')
        name='/'.join(parts); size=member['size']; is_dir=member['is_dir']
        if not isinstance(is_dir,bool) or isinstance(size,bool) or not isinstance(size,int) or size<0 or is_dir and size: raise ValueError('invalid metadata')
        if name in kinds: raise ValueError('duplicate')
        for i in range(1,len(parts)):
            parent='/'.join(parts[:i])
            if kinds.get(parent) is False: raise ValueError('file parent')
        if not is_dir and any(existing.startswith(name + '/') for existing in kinds): raise ValueError('directory conflict')
        kinds[name]=is_dir; total += 0 if is_dir else size
        if total>max_total: raise ValueError('size limit')
        result.append({'name':name,'size':size,'is_dir':is_dir})
    return sorted(result,key=lambda m:(m['name'].split('/'), not m['is_dir']))
