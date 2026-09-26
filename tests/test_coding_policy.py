import unittest
from compute_bench.coding.grading import source_policy


class CandidatePolicyTests(unittest.TestCase):
    def test_normal_type_names_and_regex_compile_are_allowed(self):
        for source in [
            'def f(value):\n return type(value).__name__\n',
            'import re\nPATTERN = re.compile("a+")\n',
            'import re as regex\nPATTERN = regex.compile("a+")\n',
            'from re import compile\nPATTERN = compile("a+")\n',
            'from __future__ import annotations\ndef f(x: int) -> int:\n return x\n',
            'import graphlib, numbers, posixpath, statistics\n',
            'import os\ndef f(x): return os.path.normpath(os.fspath(x))\n',
            'from os import path, fspath\ndef f(x): return path.normpath(fspath(x))\n',
            'from pathlib import Path, PurePosixPath\ndef f(x): return Path(x).parts, PurePosixPath(x).parts\n',
            "def f(x):\n return getattr(x, 'items', None)\n",
            'class E(ValueError):\n def __str__(self): return super().__str__()\n',
        ]:
            self.assertEqual(source_policy(source), [], source)

    def test_runtime_code_compilation_and_io_remain_out_of_scope(self):
        for source in ['compile("pass", "x", "exec")', 'import io\nf = io.open("acceptance.py")',
                       'import os\nos._exit(0)', 'import pathlib\npathlib.Path("acceptance.py").read_text()',
                       'from configparser import ConfigParser\nConfigParser().read("acceptance.py")',
                       "getattr(path, 'read_text')", "getattr(f, '__globals__')",
                       'name="items"\ngetattr(x, name)', 'print("__BENCH_GRADE__={}")']:
            self.assertTrue(source_policy(source), source)


if __name__ == "__main__":
    unittest.main()
