import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [[3, 1, None, 4, 1]], 'expected': {'count': 4, 'min': 1, 'max': 4, 'range': 3}}, {'args': [[None, None]], 'expected': {'count': 0, 'min': None, 'max': None, 'range': None}}, {'args': [[7]], 'expected': {'count': 1, 'min': 7, 'max': 7, 'range': 0}}, {'args': [[-5, -1, None]], 'expected': {'count': 2, 'min': -5, 'max': -1, 'range': 4}}, {'args': [[2, 2, 2]], 'expected': {'count': 3, 'min': 2, 'max': 2, 'range': 0}}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.summarize_values(*args, **kwargs)
                else:
                    self.assertEqual(solution.summarize_values(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
