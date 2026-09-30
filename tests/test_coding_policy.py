import unittest
from compute_bench.coding.grading import grade_source, source_policy


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
            'import os.path\ndef f(x): return os.path.join("a", x)\n',
            'from os import path, fspath\ndef f(x): return path.normpath(fspath(x))\n',
            'from pathlib import Path, PurePosixPath\ndef f(x): return Path(x).parts, PurePosixPath(x).parts\n',
            'import inspect\ndef f(cls): return inspect.getattr_static(cls, "pytestmark", [])\n',
            'import random\ndef f(values): return random.choice(values)\n',
            'from random import randrange\ndef f(stop): return randrange(stop)\n',
            'def f(obj, marks):\n setattr(obj, "pytestmark", marks)\n',
            "def f(x):\n return getattr(x, 'items', None)\n",
            'def f(x, name):\n return getattr(x, name)\n',
            'def f(x):\n return vars(x)\n',
            'def f(x):\n return getattr(x, "_fields", None)\n',
            'def f(x):\n return getattr(x, "__dict__", None)\n',
            'def f(cls):\n return cls.__mro__\n',
            'class E(ValueError):\n def __str__(self): return super().__str__()\n',
        ]:
            self.assertEqual(source_policy(source), [], source)

    def test_runtime_code_compilation_and_io_remain_out_of_scope(self):
        for source in ['compile("pass", "x", "exec")', 'import io\nf = io.open("acceptance.py")',
                       'import os\nos._exit(0)', 'import pathlib\npathlib.Path("acceptance.py").read_text()',
                       'from configparser import ConfigParser\nConfigParser().read("acceptance.py")',
                       "getattr(path, 'read_text')", "getattr(f, '__globals__')",
                       "getattr(cls, '__mro__')",
                       'import os.path\nos.system("true")', 'print("__BENCH_GRADE__={}")']:
            self.assertTrue(source_policy(source), source)

    def test_dynamic_reflection_is_guarded_at_candidate_runtime(self):
        tests = '''import unittest, solution
class Box:
 value = 3
class T(unittest.TestCase):
 def test_public_field(self): self.assertEqual(solution.read(Box(), "value"), 3)
 def test_private_field(self):
  with self.assertRaises(AttributeError): solution.read(solution.read, "__globals__")
'''
        source = 'def read(value, name):\n return getattr(value, name)\n'
        result = grade_source(source, tests)
        self.assertTrue(result["passed"], result)

    def test_direct_mro_access_matches_the_public_mro_api(self):
        tests = '''import unittest, solution
class Base: pass
class Child(Base): pass
class T(unittest.TestCase):
 def test_lineage(self): self.assertEqual(solution.lineage(Child), Child.mro())
'''
        result = grade_source('def lineage(cls):\n return list(cls.__mro__)\n', tests)
        self.assertTrue(result["passed"], result)

    def test_vars_on_a_class_matches_direct_dict_access(self):
        tests = '''import unittest, solution
class Base: value = 1
class Child(Base): value = 2
class T(unittest.TestCase):
 def test_direct_value(self): self.assertEqual(solution.direct_value(Child), 2)
'''
        result = grade_source(
            'def direct_value(cls):\n return vars(cls)["value"]\n', tests)
        self.assertTrue(result["passed"], result)

    def test_setattr_is_available_at_candidate_runtime(self):
        tests = '''import unittest, solution
class Box: pass
class T(unittest.TestCase):
 def test_assignment(self):
  box = Box()
  self.assertEqual(solution.assign(box, "value", 3), 3)
  self.assertEqual(box.value, 3)
'''
        result = grade_source(
            'def assign(obj, name, value):\n setattr(obj, name, value)\n return getattr(obj, name)\n',
            tests,
        )
        self.assertTrue(result["passed"], result)


if __name__ == "__main__":
    unittest.main()
