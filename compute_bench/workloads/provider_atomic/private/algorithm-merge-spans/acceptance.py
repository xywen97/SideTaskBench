import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [[[5, 8], [1, 3], [3, 6]]], 'expected': [(1, 8)], 'no_mutation': True}, {'args': [[[-3, -1], [0, 2]]], 'expected': [(-3, -1), (0, 2)]}, {'args': [[[2, 1]]], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.merge_spans(*args, **kwargs)
                else:
                    self.assertEqual(solution.merge_spans(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
