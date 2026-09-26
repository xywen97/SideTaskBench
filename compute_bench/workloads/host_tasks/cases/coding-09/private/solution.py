import re

def build_copy_plan(root, entries):
    if not isinstance(root, str) or not root or root.startswith(('/', '\\')) or '..' in root.replace('\\', '/').split('/'):
        raise ValueError('invalid root')
    root = '/'.join(part for part in root.replace('\\', '/').split('/') if part not in ('', '.'))
    if not root:
        raise ValueError('invalid root')
    result, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'path', 'size', 'sha256'}:
            raise ValueError('invalid entry')
        raw = entry['path']
        if not isinstance(raw, str) or not raw or raw.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', raw):
            raise ValueError('invalid path')
        parts = [part for part in raw.replace('\\', '/').split('/') if part not in ('', '.')]
        if not parts or '..' in parts:
            raise ValueError('unsafe path')
        path = '/'.join(parts)
        if path in seen:
            raise ValueError('duplicate path')
        seen.add(path)
        size, digest = entry['size'], entry['sha256']
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError('invalid size')
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-fA-F]{64}', digest) is None:
            raise ValueError('invalid sha256')
        result.append({'path': path, 'target': root + '/' + path, 'size': size, 'sha256': digest.lower()})
    return sorted(result, key=lambda item: item['path'])
