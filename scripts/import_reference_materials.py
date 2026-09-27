"""Refresh pinned, complete upstream documents; never execute downloaded content."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / 'compute_bench/workloads/host_tasks/cases'
RETRIEVED = '2026-09-25T09:00:05.862699+00:00'
SOURCES = {
    'python': ('python/cpython', 'cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69', 'Python 3.11.14', 'LICENSE', 'PSF license; documentation examples also under Zero-Clause BSD'),
    'aip': ('aip-dev/google.aip.dev', '23e176e7333ea3bc6b085f9950a5da03d2bbfc72', 'Pinned AIP snapshot', 'LICENSE.md', 'CC-BY-4.0; code samples Apache-2.0'),
    'boto': ('boto/boto3', 'e2fb47b057930792b8bfe192063207b8c4794395', 'Boto3 1.40.0', 'LICENSE', 'Apache-2.0'),
}
# First document is the treatment target; the remaining documents stay unchanged.
CATALOG = {
    'coding-01': [('python', 'Doc/library/csv.rst', 'Python csv — CSV File Reading and Writing'),
                  ('python', 'Doc/library/io.rst', 'Python io — Core tools for working with streams'),
                  ('python', 'Doc/tutorial/inputoutput.rst', 'Python tutorial — Input and Output')],
    'coding-02': [('python', 'Doc/library/json.rst', 'Python json — JSON encoder and decoder'),
                  ('python', 'Doc/tutorial/inputoutput.rst', 'Python tutorial — Input and Output'),
                  ('python', 'Doc/tutorial/errors.rst', 'Python tutorial — Errors and Exceptions')],
    'coding-03': [('python', 'Doc/library/urllib.parse.rst', 'Python urllib.parse — Parse URLs into components'),
                  ('python', 'Doc/library/urllib.request.rst', 'Python urllib.request — Extensible library for opening URLs'),
                  ('python', 'Doc/howto/urllib2.rst', 'Python HOWTO — Fetch Internet Resources Using urllib')],
    'coding-04': [('python', 'Doc/tutorial/errors.rst', 'Python tutorial — Errors and Exceptions'),
                  ('python', 'Doc/tutorial/controlflow.rst', 'Python tutorial — More Control Flow Tools'),
                  ('python', 'Doc/library/exceptions.rst', 'Python — Built-in Exceptions')],
    'coding-05': [('python', 'Doc/library/collections.rst', 'Python collections — Container datatypes'),
                  ('python', 'Doc/library/functools.rst', 'Python functools — Higher-order functions and operations on callable objects'),
                  ('python', 'Doc/tutorial/datastructures.rst', 'Python tutorial — Data Structures')],
    'coding-06': [('python', 'Doc/library/datetime.rst', 'Python datetime — Basic date and time types'),
                  ('python', 'Doc/library/zoneinfo.rst', 'Python zoneinfo — IANA time zone support'),
                  ('python', 'Doc/library/time.rst', 'Python time — Time access and conversions')],
    'coding-07': [('aip', 'aip/general/0158.md', 'Google AIP-158 — Pagination'),
                  ('boto', 'docs/source/guide/paginators.rst', 'Boto3 guide — Paginators'),
                  ('python', 'Doc/tutorial/datastructures.rst', 'Python tutorial — Data Structures: queues, sets and dictionaries')],
    'coding-08': [('python', 'Doc/library/graphlib.rst', 'Python graphlib — Functionality to operate with graph-like structures'),
                  ('python', 'Doc/library/heapq.rst', 'Python heapq — Heap queue algorithm'),
                  ('python', 'Doc/library/bisect.rst', 'Python bisect — Array bisection algorithm')],
}


def url(source, path, raw=True):
    repo, commit, *_ = SOURCES[source]
    host = 'https://raw.githubusercontent.com' if raw else 'https://github.com'
    return f'{host}/{repo}/{commit}/{path}' if raw else f'{host}/{repo}/blob/{commit}/{path}'


def fetch(key):
    source, path = key
    with urlopen(Request(url(source, path), headers={'User-Agent': 'create-bench-reference-import'}), timeout=45) as response:
        data = response.read()
    text = data.decode('utf-8')
    if not text.strip() or '<html' in text[:300].lower():
        raise ValueError('Expected upstream documentation source: ' + str(key))
    return key, data


def main():
    keys = {(source, path) for docs in CATALOG.values() for source, path, _ in docs}
    keys.update((source, config[3]) for source, config in SOURCES.items())
    keys.add(('python', 'Doc/license.rst'))
    keys.add(('boto', 'NOTICE'))
    # Complete all downloads before changing task files.
    with ThreadPoolExecutor(max_workers=6) as executor:
        fetched = dict(executor.map(fetch, sorted(keys)))
    retrieved = RETRIEVED
    for case_id, docs in CATALOG.items():
        root = ROOT / case_id
        metadata = json.loads((root / 'task.json').read_text())
        records = []
        for index, (source, path, title) in enumerate(docs):
            repo, commit, version, license_path, license_name = SOURCES[source]
            data = fetched[source, path]
            if len(data) < 4000:
                raise ValueError('Reference chapter unexpectedly short: ' + path)
            name = 'reference.md' if index == 0 else f'{index + 1:02d}-{Path(path).stem}{Path(path).suffix}'
            destination = 'docs/reference.md' if index == 0 else 'docs/references/' + name
            # Preserve upstream bytes exactly. Provenance is supplied by the document index.
            (root / 'reference' / name).write_bytes(data)
            license_file = f'{source}-LICENSE.txt'
            (root / 'reference' / license_file).write_bytes(fetched[source, license_path])
            if source == 'python':
                (root / 'reference/python-DOC-LICENSE.rst').write_bytes(fetched['python', 'Doc/license.rst'])
            if source == 'boto':
                (root / 'reference/boto-NOTICE.txt').write_bytes(fetched['boto', 'NOTICE'])
            records.append({'path': 'reference/' + name, 'workspace_path': destination, 'title': title,
                            'source_url': url(source, path, raw=False), 'download_url': url(source, path),
                            'upstream_repository': repo, 'upstream_commit': commit, 'version': version,
                            'format': Path(path).suffix.lstrip('.'), 'retrieved_at': retrieved,
                            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                            'lines': len(data.splitlines()), 'words': len(data.decode().split()),
                            'license': license_name, 'license_path': 'reference/' + license_file,
                            'license_url': url(source, license_path, raw=False),
                            'transform': 'none; full upstream source, original bytes'})
        metadata['reference']['documents'] = records
        metadata['reference']['path'] = records[0]['path']
        (root / 'task.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        print(case_id, [(r['workspace_path'], r['lines'], r['words']) for r in records])


if __name__ == '__main__':
    main()
