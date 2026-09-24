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
        ]:
            self.assertEqual(source_policy(source), [], source)

    def test_runtime_code_compilation_and_io_remain_out_of_scope(self):
        for source in ['compile("pass", "x", "exec")', 'import io\nf = io.open("acceptance.py")', 'import os\nos._exit(0)', 'print("__BENCH_GRADE__={}")']:
            self.assertTrue(source_policy(source), source)


if __name__ == "__main__":
    unittest.main()
