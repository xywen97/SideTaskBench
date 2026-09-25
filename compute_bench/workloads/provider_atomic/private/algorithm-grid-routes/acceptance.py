import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [3, 3, [[1, 1]]], 'expected': 2, 'no_mutation': True}, {'args': [1, 1, []], 'expected': 1}, {'args': [2, 2, [[0, 0]]], 'expected': 0}, {'args': [2, 2, [[2, 0]]], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.count_routes(*args, **kwargs)
                else:
                    self.assertEqual(solution.count_routes(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
