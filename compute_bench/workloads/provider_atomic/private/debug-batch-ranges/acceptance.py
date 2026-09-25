import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [5, 2], 'expected': [(0, 2), (2, 4), (4, 5)]}, {'args': [0, 3], 'expected': []}, {'args': [3, True], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.batch_ranges(*args, **kwargs)
                else:
                    self.assertEqual(solution.batch_ranges(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
