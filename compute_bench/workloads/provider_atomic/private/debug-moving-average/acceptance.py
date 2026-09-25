import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [[1, 2, 3, 4], 2], 'expected': [1.5, 2.5, 3.5], 'no_mutation': True}, {'args': [[2, 4], 2], 'expected': [3.0]}, {'args': [[], 1], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.moving_average(*args, **kwargs)
                else:
                    self.assertEqual(solution.moving_average(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
