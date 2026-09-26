"""Generate coding-09..coding-16 and their pinned CPython reference collections."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "compute_bench/workloads/host_tasks/cases"
COMMIT = "cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69"
BASE = f"https://raw.githubusercontent.com/python/cpython/{COMMIT}/Doc/"
SOURCE_BASE = f"https://github.com/python/cpython/blob/{COMMIT}/Doc/"
VERSION = "Python 3.11.14"
RETRIEVED = "2026-09-25T09:00:05.862699+00:00"


DOCS = {
    "pathlib": ("library/pathlib.rst", "Python pathlib — Object-oriented filesystem paths", ["path", "filesystem", "relative", "absolute", "parts"]),
    "ospath": ("library/os.path.rst", "Python os.path — Common pathname manipulations", ["path", "normalize", "absolute", "commonpath", "basename"]),
    "fnmatch": ("library/fnmatch.rst", "Python fnmatch — Unix filename pattern matching", ["glob", "pattern", "filename", "match"]),
    "hashlib": ("library/hashlib.rst", "Python hashlib — Secure hashes and message digests", ["digest", "sha256", "hash", "hexdigest"]),
    "shutil": ("library/shutil.rst", "Python shutil — High-level file operations", ["copy", "filesystem", "archive", "metadata"]),
    "exceptions": ("library/exceptions.rst", "Python built-in exceptions", ["valueerror", "typeerror", "exception", "validation"]),
    "email_message": ("library/email.message.rst", "Python email.message — Representing an email message", ["header", "email", "message", "duplicate"]),
    "email_policy": ("library/email.policy.rst", "Python email.policy — Parsing policy controls", ["header", "policy", "validation", "line"]),
    "email_utils": ("library/email.utils.rst", "Python email.utils — Miscellaneous utilities", ["email", "address", "mailbox", "parseaddr"]),
    "urllib_request": ("library/urllib.request.rst", "Python urllib.request — Request headers", ["http", "header", "request", "connection"]),
    "http_client": ("library/http.client.rst", "Python http.client — HTTP protocol client", ["http", "header", "connection", "transfer"]),
    "re": ("library/re.rst", "Python re — Regular expression operations", ["token", "validation", "pattern", "header"]),
    "configparser": ("library/configparser.rst", "Python configparser — Configuration file parser", ["config", "layer", "default", "interpolation"]),
    "json": ("library/json.rst", "Python json — JSON encoder and decoder", ["config", "object", "list", "number"]),
    "dataclasses": ("library/dataclasses.rst", "Python dataclasses — Data classes", ["settings", "field", "default", "copy"]),
    "decimal": ("library/decimal.rst", "Python decimal — Decimal arithmetic", ["number", "timeout", "parse", "finite"]),
    "collections": ("library/collections.rst", "Python collections — Container data types", ["mapping", "order", "layer", "counter"]),
    "typing": ("library/typing.rst", "Python typing — Type hints", ["mapping", "iterable", "sequence", "config"]),
    "zipfile": ("library/zipfile.rst", "Python zipfile — Work with ZIP archives", ["archive", "member", "directory", "extract"]),
    "tarfile": ("library/tarfile.rst", "Python tarfile — Read and write tar archives", ["archive", "member", "extract", "path"]),
    "tempfile": ("library/tempfile.rst", "Python tempfile — Temporary files and directories", ["archive", "temporary", "directory", "cleanup"]),
    "stat": ("library/stat.rst", "Python stat — File mode constants", ["file", "directory", "mode", "metadata"]),
    "io": ("library/io.rst", "Python io — Core stream tools", ["stream", "bytes", "size", "file"]),
    "shlex": ("library/shlex.rst", "Python shlex — Simple lexical analysis", ["shell", "quote", "pipeline", "token"]),
    "statistics": ("library/statistics.rst", "Python statistics — Mathematical statistics", ["mean", "average", "data", "numeric"]),
    "math": ("library/math.rst", "Python math — Mathematical functions", ["finite", "nan", "infinity", "number"]),
    "itertools": ("library/itertools.rst", "Python itertools — Iterator building blocks", ["window", "iterator", "sequence", "sliding"]),
    "bisect": ("library/bisect.rst", "Python bisect — Array bisection", ["sorted", "order", "window", "sequence"]),
    "fractions": ("library/fractions.rst", "Python fractions — Rational numbers", ["number", "ratio", "mean", "numeric"]),
    "functions": ("tutorial/controlflow.rst", "Python tutorial — Defining functions", ["argument", "function", "validation", "default"]),
    "graphlib": ("library/graphlib.rst", "Python graphlib — Topological sorting", ["graph", "dependency", "cycle", "topological"]),
    "heapq": ("library/heapq.rst", "Python heapq — Heap queue algorithm", ["priority", "stable", "ready", "order"]),
    "sets": ("library/stdtypes.rst", "Python built-in set and mapping types", ["set", "dict", "dependency", "mapping"]),
    "copy": ("library/copy.rst", "Python copy — Shallow and deep copy", ["copy", "mutation", "graph", "object"]),
    "enum": ("library/enum.rst", "Python enum — Enumerations", ["state", "status", "batch", "value"]),
    "string": ("library/string.rst", "Python string — Common string operations", ["string", "identifier", "template", "token"]),
    "subprocess": ("library/subprocess.rst", "Python subprocess — Subprocess management", ["command", "argv", "shell", "pipeline"]),
    "argparse": ("library/argparse.rst", "Python argparse — Command-line parsing", ["argument", "option", "command", "argv"]),
}


COMMON_LICENSE_FROM = CASES / "coding-01/reference/python-LICENSE.txt"
COMMON_DOC_LICENSE_FROM = CASES / "coding-01/reference/python-DOC-LICENSE.rst"


def test_module(test_body: str) -> str:
    return "import unittest\nimport solution\n\n\nclass Tests(unittest.TestCase):\n" + test_body + "\n\nif __name__ == '__main__':\n    unittest.main()\n"


TASKS = [
    {
        "id": "coding-09", "title": "Build a deterministic and safe file copy manifest",
        "topic": "Python path normalization relative paths SHA-256 manifest deterministic ordering",
        "context": "Filesystem compatibility checks exercise one independent pure data transformation.",
        "function": "build_copy_plan(root, entries)",
        "requirements": "Normalize POSIX and backslash separators, reject absolute paths and traversal, validate nonnegative sizes and 64-digit SHA-256 digests, normalize accepted digests to lowercase, reject normalized duplicates, preserve the input, and return records sorted by normalized path with targets rooted below root.",
        "broken": "def build_copy_plan(root, entries):\n    return [{**entry, 'target': root + '/' + entry['path']} for entry in entries]\n",
        "fixed": '''import re

def build_copy_plan(root, entries):
    if not isinstance(root, str) or not root or root.startswith(('/', '\\\\')) or '..' in root.replace('\\\\', '/').split('/'):
        raise ValueError('invalid root')
    root = '/'.join(part for part in root.replace('\\\\', '/').split('/') if part not in ('', '.'))
    if not root:
        raise ValueError('invalid root')
    result, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'path', 'size', 'sha256'}:
            raise ValueError('invalid entry')
        raw = entry['path']
        if not isinstance(raw, str) or not raw or raw.startswith(('/', '\\\\')) or re.match(r'^[A-Za-z]:', raw):
            raise ValueError('invalid path')
        parts = [part for part in raw.replace('\\\\', '/').split('/') if part not in ('', '.')]
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
''',
        "public": test_module("""    def test_normalizes_and_sorts(self):
        d = 'A' * 64
        got = solution.build_copy_plan('dst', [{'path':'b.txt','size':2,'sha256':d}, {'path':'a/./x','size':0,'sha256':d}])
        self.assertEqual([x['path'] for x in got], ['a/x','b.txt'])
        self.assertEqual(got[0]['target'], 'dst/a/x')

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError): solution.build_copy_plan('dst', [{'path':'../x','size':1,'sha256':'0'*64}])

    def test_backslashes_duplicates_and_strict_metadata(self):
        got = solution.build_copy_plan('dst', [{'path':'a\\\\b','size':1,'sha256':'AB'*32}])
        self.assertEqual(got[0]['path'], 'a/b')
        self.assertEqual(got[0]['sha256'], 'ab'*32)
        with self.assertRaises(ValueError):
            solution.build_copy_plan('dst', [{'path':'a/b','size':1,'sha256':'0'*64}, {'path':'a//b','size':1,'sha256':'1'*64}])
        for size in (True, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                solution.build_copy_plan('dst', [{'path':'x','size':size,'sha256':'0'*64}])"""),
        "hidden": test_module("""    def test_backslash_and_digest_case(self):
        got = solution.build_copy_plan('out/root', [{'path':'a\\\\b.txt','size':1,'sha256':'AB'*32}])
        self.assertEqual(got, [{'path':'a/b.txt','target':'out/root/a/b.txt','size':1,'sha256':'ab'*32}])

    def test_duplicate_after_normalization(self):
        e=[{'path':'a/b','size':1,'sha256':'0'*64},{'path':'a//b','size':1,'sha256':'1'*64}]
        with self.assertRaises(ValueError): solution.build_copy_plan('dst', e)

    def test_absolute_drive_size_and_digest(self):
        base={'size':1,'sha256':'0'*64}
        for path in ['/x','C:\\\\x']:
            with self.subTest(path=path), self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':path,**base}])
        for size in [-1, True, 1.5]:
            with self.subTest(size=size), self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':'x','size':size,'sha256':'0'*64}])
        with self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':'x','size':1,'sha256':'x'}])

    def test_no_mutation(self):
        e=[{'path':'a','size':1,'sha256':'0'*64}]; before=[dict(e[0])]
        solution.build_copy_plan('dst',e); self.assertEqual(e,before)"""),
        "docs": ["pathlib", "ospath", "fnmatch", "hashlib", "shutil", "exceptions"],
    },
    {
        "id": "coding-10", "title": "Merge HTTP headers without forwarding hop-by-hop state",
        "topic": "Python HTTP header validation case insensitive singleton hop-by-hop Connection",
        "context": "HTTP compatibility checks exercise one independent normalized record example.",
        "function": "merge_headers(base, updates)",
        "requirements": "Both inputs are ordered iterables of `(name, value)` string pairs. Validate header names and values, normalize names to lowercase and trim optional whitespace, remove standard hop-by-hop fields plus fields named by Connection, append ordinary repeated fields, replace singleton host/content-length/content-type fields using the last update, preserve order, and never mutate inputs.",
        "broken": "def merge_headers(base, updates):\n    values = dict(base)\n    values.update(updates)\n    return list(values.items())\n",
        "fixed": '''import re

_TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_HOP = {'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade'}
_SINGLE = {'host','content-length','content-type'}

def merge_headers(base, updates):
    pairs = []
    for name, value in list(base) + list(updates):
        if not isinstance(name, str) or _TOKEN.fullmatch(name) is None or not isinstance(value, str) or '\\r' in value or '\\n' in value:
            raise ValueError('invalid header')
        pairs.append((name.lower(), value.strip(' \\t')))
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
''',
        "public": test_module("""    def test_case_insensitive_replacement_and_append(self):
        got=solution.merge_headers([('Content-Type',' text/plain '),('X-A','1')],[('content-type','application/json'),('X-A','2')])
        self.assertEqual(got,[('x-a','1'),('content-type','application/json'),('x-a','2')])

    def test_strips_hop_headers(self):
        self.assertEqual(solution.merge_headers([('Connection','X-Trace'),('X-Trace','secret'),('X-End','ok')],[]),[('x-end','ok')])

    def test_rejects_invalid_names_and_injection(self):
        for pair in [(('Bad Name','x'),), (('X-Test','a\\nb'),)]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                solution.merge_headers(pair, [])"""),
        "hidden": test_module("""    def test_standard_hop_headers_removed(self):
        got=solution.merge_headers([('TE','trailers'),('Upgrade','websocket'),('X',' y ')], [('Keep-Alive','x')])
        self.assertEqual(got,[('x','y')])

    def test_singletons_use_last_update(self):
        got=solution.merge_headers([('Host','a')],[('host','b'),('HOST','c'),('Content-Length','2')])
        self.assertEqual(got,[('host','c'),('content-length','2')])

    def test_rejects_injection_and_bad_name(self):
        for pair in [(('Bad Name','x'),),(('X','a\\nb'),)]:
            with self.subTest(pair=pair), self.assertRaises(ValueError): solution.merge_headers(pair,[])

    def test_no_mutation(self):
        base=[('X',' 1 ')]; updates=[('Y','2')]; solution.merge_headers(base,updates)
        self.assertEqual(base,[('X',' 1 ')]); self.assertEqual(updates,[('Y','2')])"""),
        "docs": ["http_client", "urllib_request", "email_message", "email_policy", "re", "exceptions"],
    },
    {
        "id": "coding-11", "title": "Resolve layered typed configuration without mutating inputs",
        "topic": "Python layered configuration typed values defaults validation deterministic merge",
        "context": "Configuration compatibility checks exercise one independent settings conversion.",
        "function": "resolve_settings(layers)",
        "requirements": "Apply layers in order over fixed defaults timeout=5.0, retries=3, enabled=True, tags=[]. Timeout accepts a positive finite number or numeric string; retries accepts a nonnegative integer or decimal-digit string. Enabled accepts a boolean or the case-insensitive ConfigParser spellings `true`/`false`, `yes`/`no`, `on`/`off`, and `1`/`0`. None resets a key to its default. Tags accept a comma string or an iterable of strings, are trimmed, and are deduplicated in order. Reject unknown keys, bool-as-number, and all other values; return fresh data without mutation.",
        "broken": "def resolve_settings(layers):\n    result = {}\n    for layer in layers: result.update(layer)\n    return result\n",
        "fixed": '''import math

_DEFAULTS = {'timeout':5.0,'retries':3,'enabled':True,'tags':[]}

def resolve_settings(layers):
    result = {'timeout':5.0,'retries':3,'enabled':True,'tags':[]}
    for layer in layers:
        if not isinstance(layer, dict) or set(layer) - set(_DEFAULTS):
            raise ValueError('invalid layer')
        for key, value in layer.items():
            if value is None:
                result[key] = list(_DEFAULTS[key]) if key == 'tags' else _DEFAULTS[key]
            elif key == 'timeout':
                if isinstance(value, bool): raise ValueError('invalid timeout')
                try: parsed = float(value)
                except (TypeError, ValueError): raise ValueError('invalid timeout')
                if not math.isfinite(parsed) or parsed <= 0: raise ValueError('invalid timeout')
                result[key] = parsed
            elif key == 'retries':
                if isinstance(value, bool) or (isinstance(value, str) and not value.strip().isdigit()): raise ValueError('invalid retries')
                try: parsed = int(value)
                except (TypeError, ValueError): raise ValueError('invalid retries')
                if parsed < 0 or isinstance(value, float) and not value.is_integer(): raise ValueError('invalid retries')
                result[key] = parsed
            elif key == 'enabled':
                if isinstance(value, bool): result[key] = value
                elif isinstance(value, str) and value.strip().lower() in {'true','yes','on','1','false','no','off','0'}:
                    result[key] = value.strip().lower() in {'true','yes','on','1'}
                else: raise ValueError('invalid enabled')
            else:
                try: values = value.split(',') if isinstance(value, str) else list(value)
                except TypeError: raise ValueError('invalid tags')
                tags = []
                for item in values:
                    if not isinstance(item, str): raise ValueError('invalid tag')
                    item = item.strip()
                    if item and item not in tags: tags.append(item)
                result[key] = tags
    return result
''',
        "public": test_module("""    def test_layers_and_types(self):
        got=solution.resolve_settings([{'timeout':'2.5','tags':'a, b,a'},{'enabled':'false','retries':'0'}])
        self.assertEqual(got,{'timeout':2.5,'retries':0,'enabled':False,'tags':['a','b']})

    def test_none_resets_default(self):
        self.assertEqual(solution.resolve_settings([{'timeout':2},{'timeout':None}])['timeout'],5.0)

    def test_strict_value_domains(self):
        self.assertTrue(solution.resolve_settings([{'enabled':'yes'}])['enabled'])
        self.assertFalse(solution.resolve_settings([{'enabled':'OFF'}])['enabled'])
        for layer in ({'enabled':'maybe'}, {'timeout':'nan'}, {'retries':1.5}, {'tags':['x',1]}):
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                solution.resolve_settings([layer])"""),
        "hidden": test_module("""    def test_defaults_are_fresh(self):
        a=solution.resolve_settings([]); b=solution.resolve_settings([]); a['tags'].append('x'); self.assertEqual(b['tags'],[])

    def test_unknown_and_invalid_values(self):
        for layer in [{'x':1},{'timeout':True},{'timeout':'nan'},{'retries':1.5},{'enabled':'maybe'},{'tags':['x',1]}]:
            with self.subTest(layer=layer), self.assertRaises(ValueError): solution.resolve_settings([layer])

    def test_iterable_tags_and_reset(self):
        got=solution.resolve_settings([{'tags':(' a ','b','a')},{'tags':None}]); self.assertEqual(got['tags'],[])

    def test_no_mutation(self):
        layers=[{'tags':['a','b']}]; solution.resolve_settings(layers); self.assertEqual(layers,[{'tags':['a','b']}])"""),
        "docs": ["configparser", "json", "dataclasses", "decimal", "collections", "typing"],
    },
    {
        "id": "coding-12", "title": "Validate an archive extraction plan before writing files",
        "topic": "Python archive extraction path traversal duplicate members file directory conflicts size limit",
        "context": "Archive compatibility checks exercise one independent safe path manifest.",
        "function": "plan_archive(members, max_total)",
        "requirements": "Each member has exactly the fields name/size/is_dir. Normalize slash separators; reject absolute and traversal paths, duplicates, descendants below files, and file/directory conflicts. Sizes and `max_total` are nonnegative non-boolean integers, `is_dir` is boolean, and directories have size zero. Enforce the total file-size limit, preserve input, and return normalized members with directories before descendants in deterministic path order.",
        "broken": "def plan_archive(members, max_total):\n    return list(members)\n",
        "fixed": '''import re

def plan_archive(members, max_total):
    if isinstance(max_total, bool) or not isinstance(max_total, int) or max_total < 0: raise ValueError('invalid limit')
    result, kinds, total = [], {}, 0
    for member in members:
        if not isinstance(member, dict) or set(member) != {'name','size','is_dir'}: raise ValueError('invalid member')
        raw=member['name']
        if not isinstance(raw,str) or not raw or raw.startswith(('/', '\\\\')) or re.match(r'^[A-Za-z]:',raw): raise ValueError('unsafe name')
        parts=[p for p in raw.replace('\\\\','/').split('/') if p not in ('','.')]
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
''',
        "public": test_module("""    def test_normalizes_and_orders(self):
        got=solution.plan_archive([{'name':'a\\\\b.txt','size':2,'is_dir':False},{'name':'a','size':0,'is_dir':True}],2)
        self.assertEqual([x['name'] for x in got],['a','a/b.txt'])

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'../x','size':1,'is_dir':False}],2)

    def test_strict_limit_and_file_parent(self):
        for limit in (True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                solution.plan_archive([], limit)
        with self.assertRaises(ValueError):
            solution.plan_archive([{'name':'x','size':1,'is_dir':False}, {'name':'x/y','size':1,'is_dir':False}], 2)"""),
        "hidden": test_module("""    def test_size_limit_and_directory_size(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':3,'is_dir':False}],2)
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'d','size':1,'is_dir':True}],2)

    def test_duplicate_and_file_parent(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':0,'is_dir':True},{'name':'x/','size':0,'is_dir':True}],0)
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':1,'is_dir':False},{'name':'x/y','size':1,'is_dir':False}],2)

    def test_descendant_before_file_conflict(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x/y','size':1,'is_dir':False},{'name':'x','size':1,'is_dir':False}],2)

    def test_invalid_limit_and_no_mutation(self):
        for limit in [-1,True,1.5]:
            with self.subTest(limit=limit), self.assertRaises(ValueError): solution.plan_archive([],limit)
        m=[{'name':'x','size':1,'is_dir':False}]; solution.plan_archive(m,1); self.assertEqual(m,[{'name':'x','size':1,'is_dir':False}])"""),
        "docs": ["zipfile", "tarfile", "pathlib", "tempfile", "stat", "io"],
    },
    {
        "id": "coding-13", "title": "Compute rolling summaries with missing observations",
        "topic": "Python rolling window statistics missing values finite numbers minimum observations",
        "context": "Statistics compatibility checks exercise one independent numeric window example.",
        "function": "rolling_summary(values, width, min_valid=1)",
        "requirements": "Materialize any finite iterable, including a one-shot generator, without mutating its source. For each complete consecutive window return start/count/mean/min/max. Values may be built-in int/float or None; None is missing, while bool, strings, and nonfinite numbers are invalid. Width is a positive non-boolean integer no larger than the materialized input; min_valid is a positive non-boolean integer no larger than width. When count is below min_valid, return None for all three statistics.",
        "broken": "def rolling_summary(values, width, min_valid=1):\n    return [{'mean': sum(values[i:i+width])/width} for i in range(len(values)-width+1)]\n",
        "fixed": '''import math

def rolling_summary(values, width, min_valid=1):
    data=list(values)
    if isinstance(width,bool) or not isinstance(width,int) or width<=0 or width>len(data): raise ValueError('invalid width')
    if isinstance(min_valid,bool) or not isinstance(min_valid,int) or not 1<=min_valid<=width: raise ValueError('invalid min_valid')
    for value in data:
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
            raise ValueError('invalid value')
    result=[]
    for start in range(len(data)-width+1):
        present=[v for v in data[start:start+width] if v is not None]
        enough=len(present)>=min_valid
        result.append({'start':start,'count':len(present),'mean':sum(present)/len(present) if enough else None,
                       'min':min(present) if enough else None,'max':max(present) if enough else None})
    return result
''',
        "public": test_module("""    def test_missing_values_and_threshold(self):
        got=solution.rolling_summary([1,None,3,5],3,2)
        self.assertEqual(got,[{'start':0,'count':2,'mean':2.0,'min':1,'max':3},{'start':1,'count':2,'mean':4.0,'min':3,'max':5}])

    def test_below_threshold(self):
        self.assertEqual(solution.rolling_summary([None,2],2,2)[0]['mean'],None)

    def test_generator_and_strict_numeric_values(self):
        got = solution.rolling_summary((x for x in [1,2,3]), 2)
        self.assertEqual([x['mean'] for x in got], [1.5, 2.5])
        for value in (True, float('nan'), float('inf'), '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.rolling_summary([value], 1)
        with self.assertRaises(ValueError):
            solution.rolling_summary([1], 1, True)"""),
        "hidden": test_module("""    def test_all_windows_and_generator(self):
        got=solution.rolling_summary((x for x in [1,2,3]),2); self.assertEqual([x['mean'] for x in got],[1.5,2.5])

    def test_invalid_dimensions(self):
        for args in [([1],0,1),([1],2,1),([1],1,0),([1],1,2),([1],True,1),([1],1,True)]:
            with self.subTest(args=args), self.assertRaises(ValueError): solution.rolling_summary(*args)

    def test_invalid_values(self):
        for value in [True,float('nan'),float('inf'),'1']:
            with self.subTest(value=value), self.assertRaises(ValueError): solution.rolling_summary([value],1)

    def test_no_mutation(self):
        values=[1,None,2]; solution.rolling_summary(values,2); self.assertEqual(values,[1,None,2])"""),
        "docs": ["statistics", "math", "itertools", "collections", "bisect", "fractions"],
    },
    {
        "id": "coding-14", "title": "Schedule only the dependency closure in stable batches",
        "topic": "Python dependency graph target closure stable topological batches cycle validation",
        "context": "Dependency compatibility checks exercise one independent stable ordering example.",
        "function": "stable_batches(graph, targets=None)",
        "requirements": "Validate nonempty string nodes and dependency iterables, include dependency-only nodes, and optionally restrict scheduling to the transitive dependency closure of targets. Deduplicate edges, emit lexicographically sorted parallel-ready batches, reject unknown targets and cycles in the selected closure, and do not mutate graph.",
        "broken": "def stable_batches(graph, targets=None):\n    return [sorted(graph)]\n",
        "fixed": '''def stable_batches(graph, targets=None):
    deps={}
    for node, values in graph.items():
        if not isinstance(node,str) or not node: raise ValueError('invalid node')
        try: values=list(values)
        except TypeError: raise ValueError('invalid dependencies')
        if any(not isinstance(v,str) or not v for v in values): raise ValueError('invalid dependency')
        deps[node]=set(values)
    for values in list(deps.values()):
        for value in values: deps.setdefault(value,set())
    if targets is None:
        selected=set(deps)
    else:
        try: pending=list(targets)
        except TypeError: raise ValueError('invalid targets')
        if any(t not in deps for t in pending): raise ValueError('unknown target')
        selected=set()
        while pending:
            node=pending.pop()
            if node not in selected: selected.add(node); pending.extend(deps[node])
    remaining={n:deps[n]&selected for n in selected}; batches=[]
    while remaining:
        ready=sorted(n for n,d in remaining.items() if not d)
        if not ready: raise ValueError('cycle')
        batches.append(ready); done=set(ready)
        remaining={n:(d-done) for n,d in remaining.items() if n not in done}
    return batches
''',
        "public": test_module("""    def test_batches_and_dependency_only_nodes(self):
        self.assertEqual(solution.stable_batches({'build':['lint','test'],'test':['compile']}),[['compile','lint'],['test'],['build']])

    def test_target_closure(self):
        self.assertEqual(solution.stable_batches({'a':['b'],'b':[],'x':[]},['a']),[['b'],['a']])

    def test_cycles_are_invalid(self):
        with self.assertRaises(ValueError): solution.stable_batches({'a':['b'],'b':['a']})
        with self.assertRaises(ValueError): solution.stable_batches({'a':[]}, ['missing'])
        with self.assertRaises(ValueError): solution.stable_batches({1:[]})"""),
        "hidden": test_module("""    def test_deduplicates_and_sorts(self):
        self.assertEqual(solution.stable_batches({'z':['a','a'],'a':[]}),[['a'],['z']])

    def test_cycle_selected_and_unselected(self):
        graph={'a':['b'],'b':['a'],'x':[]}
        with self.assertRaises(ValueError): solution.stable_batches(graph)
        self.assertEqual(solution.stable_batches(graph,['x']),[['x']])

    def test_unknown_and_invalid(self):
        with self.assertRaises(ValueError): solution.stable_batches({'a':[]},['x'])
        with self.assertRaises(ValueError): solution.stable_batches({1:[]})

    def test_no_mutation(self):
        graph={'a':['b'],'b':[]}; solution.stable_batches(graph); self.assertEqual(graph,{'a':['b'],'b':[]})"""),
        "docs": ["graphlib", "heapq", "collections", "sets", "copy", "enum"],
    },
    {
        "id": "coding-15", "title": "Parse a quoted shell pipeline into structured commands",
        "topic": "Python shlex quoted command pipeline environment assignment comment parsing",
        "context": "Command compatibility checks exercise one independent token normalization example.",
        "function": "parse_pipeline(text)",
        "requirements": "Use shell-like quoting and comments to parse one pipeline into stages; split only unquoted pipes; collect leading NAME=value assignments into env with last value winning; require a nonempty argv in every stage; reject empty stages, invalid assignment names, and assignment tokens after argv; preserve quoted spaces and never execute commands.",
        "broken": "def parse_pipeline(text):\n    return [{'env': {}, 'argv': part.strip().split()} for part in text.split('|')]\n",
        "fixed": '''import re
import shlex

_NAME=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def parse_pipeline(text):
    if not isinstance(text,str): raise ValueError('invalid text')
    lexer=shlex.shlex(text,posix=True,punctuation_chars='|')
    lexer.whitespace_split=True; lexer.commenters='#'
    tokens=[piece for token in lexer for piece in ((list(token) if token and set(token) == {'|'} else [token]))]
    stages=[]; current=[]
    for token in tokens + ['|']:
        if token == '|':
            if not current: raise ValueError('empty stage')
            env={}; argv=[]
            for item in current:
                if '=' in item:
                    name,value=item.split('=',1)
                    if not argv:
                        if _NAME.fullmatch(name) is None: raise ValueError('invalid assignment')
                        env[name]=value; continue
                    if _NAME.fullmatch(name): raise ValueError('late assignment')
                argv.append(item)
            if not argv: raise ValueError('missing command')
            stages.append({'env':env,'argv':argv}); current=[]
        else: current.append(token)
    return stages
''',
        "public": test_module("""    def test_quotes_assignments_and_pipe(self):
        got=solution.parse_pipeline("A=1 echo 'a b' | grep b")
        self.assertEqual(got,[{'env':{'A':'1'},'argv':['echo','a b']},{'env':{},'argv':['grep','b']}])

    def test_comments(self):
        self.assertEqual(solution.parse_pipeline('echo x # ignored'),[{'env':{},'argv':['echo','x']}])

    def test_rejects_empty_stages_and_assignment_only(self):
        for text in ('', 'x || y', 'A=1'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                solution.parse_pipeline(text)"""),
        "hidden": test_module("""    def test_quoted_pipe_and_last_assignment(self):
        got=solution.parse_pipeline("A=1 A=2 printf 'x|y'"); self.assertEqual(got,[{'env':{'A':'2'},'argv':['printf','x|y']}])

    def test_empty_and_assignment_only(self):
        for text in ['', '| x', 'x || y', 'A=1']:
            with self.subTest(text=text), self.assertRaises(ValueError): solution.parse_pipeline(text)

    def test_invalid_and_late_assignment(self):
        for text in ['1A=x cmd','cmd A=x']:
            with self.subTest(text=text), self.assertRaises(ValueError): solution.parse_pipeline(text)

    def test_escapes(self):
        self.assertEqual(solution.parse_pipeline(r'echo a\\ b')[0]['argv'],['echo','a b'])"""),
        "docs": ["shlex", "subprocess", "argparse", "string", "re", "functions"],
    },
    {
        "id": "coding-16", "title": "Normalize and deduplicate recipient mailboxes",
        "topic": "Python email address parsing display names mailbox validation deduplication",
        "context": "Email compatibility checks exercise one independent address record conversion.",
        "function": "normalize_mailboxes(values)",
        "requirements": "Parse comma-separated display-name mailbox strings and reject CR/LF injection. An address must contain exactly one `@`, a valid local part, and one or more valid domain labels; single-label local domains are accepted. Trim display names, lowercase only the domain, deduplicate addresses case-insensitively while keeping first position, and enrich an existing entry with a later nonempty display name; preserve input and return dictionaries name/address.",
        "broken": "def normalize_mailboxes(values):\n    return [{'name':'','address':value.strip()} for value in values]\n",
        "fixed": '''import re
from email.utils import getaddresses

_LOCAL=re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_DOMAIN=re.compile(r'^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*$')

def normalize_mailboxes(values):
    raw=list(values)
    if any(not isinstance(v,str) or '\\r' in v or '\\n' in v for v in raw): raise ValueError('invalid input')
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
''',
        "public": test_module("""    def test_names_domains_and_lists(self):
        got=solution.normalize_mailboxes([' Ada  Lovelace <Ada@Example.COM>, bob@example.com'])
        self.assertEqual(got,[{'name':'Ada Lovelace','address':'Ada@example.com'},{'name':'','address':'bob@example.com'}])

    def test_deduplicates_and_enriches_name(self):
        got=solution.normalize_mailboxes(['a@example.com','Alice <A@EXAMPLE.COM>']); self.assertEqual(got,[{'name':'Alice','address':'a@example.com'}])

    def test_local_domains_and_injection(self):
        self.assertEqual(solution.normalize_mailboxes(['a@LOCALHOST']), [{'name':'','address':'a@localhost'}])
        for value in ('a@@example.com', 'a@example.com\\nBcc:x@y.com'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.normalize_mailboxes([value])"""),
        "hidden": test_module("""    def test_preserves_first_name(self):
        got=solution.normalize_mailboxes(['First <a@example.com>','Second <a@example.com>']); self.assertEqual(got[0]['name'],'First')

    def test_rejects_bad_and_injection(self):
        for value in ['not-an-address','a@example.com\\nBcc:x@y.com','a@@example.com']:
            with self.subTest(value=value), self.assertRaises(ValueError): solution.normalize_mailboxes([value])

    def test_empty(self):
        self.assertEqual(solution.normalize_mailboxes([]),[])

    def test_no_mutation(self):
        values=['A <a@example.com>']; solution.normalize_mailboxes(values); self.assertEqual(values,['A <a@example.com>'])"""),
        "docs": ["email_utils", "email_message", "email_policy", "re", "string", "exceptions"],
    },
]


def download(relative: str) -> bytes:
    cache = ROOT / ".reference-cache" / relative
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE + relative, timeout=60) as response:
            cache.write_bytes(response.read())
    return cache.read_bytes()


def write_case(spec: dict) -> None:
    directory = CASES / spec["id"]
    if directory.exists():
        shutil.rmtree(directory)
    (directory / "materials/tests").mkdir(parents=True)
    (directory / "private").mkdir()
    (directory / "reference").mkdir()
    contract = spec["requirements"] + " All validation failures must raise `ValueError`."
    instruction = (f"Fix the bugs in this Python repository: {spec['title']}.\n\n"
                   f"Implement `{spec['function']}`. {contract}\n\n"
                   "Inspect the repository, diagnose all interacting failures, and use the locally indexed "
                   "technical references as questions arise. More than one focused reference search may be "
                   "useful during diagnosis, implementation, and validation. Preserve the public API, add useful "
                   "regression coverage, run the full public test suite, and inspect the final diff.\n")
    readme = (f"# {spec['title']}\n\nThis repository contains a multi-boundary standard-library repair.\n\n"
              f"## Contract\n\n`{spec['function']}`: {contract}\n\n"
              "Implementation is in `solution.py`; public tests are in `tests/test_solution.py`.\n\n"
              "```sh\npython3 -m unittest discover -s tests -v\n```\n")
    (directory / "instructions.md").write_text(instruction)
    (directory / "materials/README.md").write_text(readme)
    (directory / "materials/solution.py").write_text(spec["broken"])
    (directory / "materials/tests/test_solution.py").write_text(spec["public"])
    (directory / "private/solution.py").write_text(spec["fixed"])
    (directory / "private/test_hidden.py").write_text(spec["hidden"])
    shutil.copy2(COMMON_LICENSE_FROM, directory / "reference/python-LICENSE.txt")
    shutil.copy2(COMMON_DOC_LICENSE_FROM, directory / "reference/python-DOC-LICENSE.rst")
    documents = []
    for index, key in enumerate(spec["docs"], 1):
        relative, title, terms = DOCS[key]
        data = download(relative)
        name = "reference.md" if index == 1 else f"{index:02d}-{Path(relative).name}"
        (directory / "reference" / name).write_bytes(data)
        text = data.decode()
        documents.append({
            "path": f"reference/{name}",
            "workspace_path": "docs/reference.md" if index == 1 else f"docs/references/{name}",
            "title": title, "source_url": SOURCE_BASE + relative,
            "download_url": BASE + relative, "upstream_repository": "python/cpython",
            "upstream_commit": COMMIT, "version": VERSION, "format": "rst",
            "retrieved_at": RETRIEVED, "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "lines": len(text.splitlines()), "words": len(text.split()),
            "license": "PSF license; documentation examples also under Zero-Clause BSD",
            "license_path": "reference/python-LICENSE.txt",
            "license_url": f"https://github.com/python/cpython/blob/{COMMIT}/LICENSE",
            "transform": "none; full upstream source, original bytes", "search_terms": terms,
        })
    manifest = {
        "schema_version": 1, "id": spec["id"], "title": spec["title"],
        "difficulty_tier": "extended", "recommended_max_steps": 70,
        "expected_reference_queries": 2,
        "user_task": "instructions.md",
        "repo_files": {"README.md": "materials/README.md", "solution.py": "materials/solution.py",
                       "tests/test_solution.py": "materials/tests/test_solution.py"},
        "reference": {"topic": spec["topic"], "path": "reference/reference.md",
                      "compatibility_context": spec["context"], "documents": documents},
        "hidden_tests": "private/test_hidden.py", "reference_files": {"solution.py": "private/solution.py"},
    }
    (directory / "task.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    for spec in TASKS:
        write_case(spec)
    catalog = json.loads((CASES / "catalog.json").read_text())
    catalog["case_ids"] = [f"coding-{index:02d}" for index in range(1, 17)]
    (CASES / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print("Generated coding-09 through coding-16")


if __name__ == "__main__":
    main()
