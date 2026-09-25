import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [[('a', 1), ('b', 2), ('a', 3)]], 'expected': {'a': [1, 3], 'b': [2]}}, {'args': [[]], 'expected': {}}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.index_pairs(*args, **kwargs)
                else:
                    self.assertEqual(solution.index_pairs(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
