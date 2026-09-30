"""Pinned long-form references reach workspaces and retrieval tools."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compute_bench.coding.environment import CodingEnvironment, create_workspace
from compute_bench.coding.tasks import build_coding_cases
from compute_bench.workloads.host_tasks import CASE_ROOT, load_host_tasks


class ReferenceCollectionsTests(unittest.TestCase):
    def test_all_hosts_have_fixed_reference_collections(self):
        cases = load_host_tasks()
        self.assertEqual(len(cases), 20)
        for case in cases:
            with self.subTest(case=case['id']):
                docs = case['reference_documents']
                expected = 6 if int(case['id'].split('-')[1]) >= 9 else 3
                self.assertEqual(len(docs), expected)
                self.assertEqual(len({d['source_url'] for d in docs}), expected)
                self.assertEqual(case['reference_text'], docs[0]['content'])
                for doc in docs:
                    data = (CASE_ROOT / case['id'] / doc['path']).read_bytes()
                    self.assertEqual(data.decode(), doc['content'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), doc['sha256'])
                    self.assertEqual(len(data), doc['bytes'])
                    self.assertGreaterEqual(doc['words'], 250)
                    self.assertGreaterEqual(doc['lines'], 50)
                    self.assertIn(doc['upstream_commit'], doc['source_url'])
                    self.assertTrue((CASE_ROOT / case['id'] / doc['license_path']).is_file())

    def test_workspace_search_and_exposure_distinguish_primary_and_companions(self):
        case = build_coding_cases(host_task_ids=['coding-01'], atomic_task_ids=['rewrite-user-record'])[0]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / 'workspace'
            with patch('compute_bench.coding.environment.Sandbox') as sandbox:
                sandbox.return_value.run.return_value = {'exit_code': 0}
                create_workspace(case, workspace, 'wrapped', 'compatibility_v3')
            with patch('microcoder.tools.shell.Sandbox'):
                env = CodingEnvironment(case, workspace, 'wrapped', variant='compatibility_v3')
            results = env.execute('search_reference', {'query': 'csv newline'})['results']
            self.assertEqual([r['path'] for r in results], [d['workspace_path'] for d in case['reference_documents']])
            readme = (workspace / 'README.md').read_text()
            self.assertIn('The reference collection is indexed by the reference search tool.', readme)
            for doc in case['reference_documents']:
                result = env.execute('read_file', {'path': doc['workspace_path']})
                self.assertEqual(env.events[-1]['reference_paths'], [doc['workspace_path']])
                if doc['workspace_path'] == 'docs/reference.md':
                    self.assertTrue(env.events[-1]['exposed'])
                    self.assertIn(case['crowd_task']['task_id'], result['content'])
                else:
                    self.assertFalse(env.events[-1]['exposed'])
                    self.assertEqual(result['content'], doc['content'])
            self.assertIn('https://github.com/python/cpython', (workspace / 'docs/reference-index.md').read_text())

    def test_primary_document_without_assigned_block_is_not_exposed(self):
        case = build_coding_cases(host_task_ids=['coding-01'],
                                  atomic_task_ids=['rewrite-user-record'])[0]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / 'workspace'
            with patch('compute_bench.coding.environment.Sandbox') as sandbox:
                sandbox.return_value.run.return_value = {'exit_code': 0}
                create_workspace(case, workspace, 'clean', 'compatibility_v4')
            with patch('microcoder.tools.shell.Sandbox'):
                env = CodingEnvironment(case, workspace, 'clean', variant='compatibility_v4')
            env.execute('read_file', {'path': 'docs/reference.md'})
            self.assertFalse(env.events[-1]['exposed'])

    def test_all_hosts_use_one_reference_search_and_readme_policy(self):
        cases = build_coding_cases(host_task_ids=['coding-01', 'coding-09'],
                                   atomic_task_ids=['rewrite-user-record'])
        readmes = []
        with tempfile.TemporaryDirectory() as temporary:
            for index, case in enumerate(cases):
                workspace = Path(temporary) / f'workspace-{index}'
                with patch('compute_bench.coding.environment.Sandbox') as sandbox:
                    sandbox.return_value.run.return_value = {'exit_code': 0}
                    create_workspace(case, workspace, 'clean', 'compatibility_v4')
                readme = (workspace / 'README.md').read_text()
                readmes.append(readme[readme.index('## Locally cached technical references'):])
                with patch('microcoder.tools.shell.Sandbox'):
                    env = CodingEnvironment(case, workspace, 'clean', variant='compatibility_v4')
                first = env.execute('search_reference', {'query': 'path validation'})['results']
                second = env.execute('search_reference', {'query': 'digest errors'})['results']
                self.assertLessEqual(len(first), 3)
                self.assertLessEqual(len(second), 3)
                expected_coverage = min(6, len(case['reference_documents']))
                self.assertEqual(len({r['path'] for r in first + second}), expected_coverage)
            self.assertEqual(readmes[0], readmes[1])

    def test_extended_reference_search_supports_follow_up_queries(self):
        case = build_coding_cases(host_task_ids=['coding-09'], atomic_task_ids=['rewrite-user-record'])[0]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / 'workspace'
            with patch('compute_bench.coding.environment.Sandbox') as sandbox:
                sandbox.return_value.run.return_value = {'exit_code': 0}
                create_workspace(case, workspace, 'clean', 'compatibility_v4')
            with patch('microcoder.tools.shell.Sandbox'):
                env = CodingEnvironment(case, workspace, 'clean', variant='compatibility_v4')
            path_results = env.execute('search_reference', {'query': 'relative path normalize'})['results']
            hash_results = env.execute('search_reference', {'query': 'sha256 digest'})['results']
            self.assertLessEqual(len(path_results), 3)
            self.assertLessEqual(len(hash_results), 3)
            self.assertNotEqual([r['path'] for r in path_results], [r['path'] for r in hash_results])

    def test_extended_follow_up_searches_cover_the_fixed_collection(self):
        case = build_coding_cases(host_task_ids=['coding-09'], atomic_task_ids=['rewrite-user-record'])[0]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / 'workspace'
            with patch('compute_bench.coding.environment.Sandbox') as sandbox:
                sandbox.return_value.run.return_value = {'exit_code': 0}
                create_workspace(case, workspace, 'clean', 'compatibility_v4')
            with patch('microcoder.tools.shell.Sandbox'):
                env = CodingEnvironment(case, workspace, 'clean', variant='compatibility_v4')
            first = env.execute('search_reference', {'query': 'path validation'})['results']
            second = env.execute('search_reference', {'query': 'digest copy errors'})['results']
            self.assertEqual(len(first), 3)
            self.assertEqual(len(second), 3)
            self.assertEqual(len({r['path'] for r in first + second}), 6)
