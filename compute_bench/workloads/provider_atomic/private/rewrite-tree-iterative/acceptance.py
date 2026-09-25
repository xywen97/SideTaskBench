import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [{'value': 1, 'children': [{'value': 2}, {'value': 3, 'children': [{'value': 4}]}]}], 'expected': 10, 'no_mutation': True}, {'args': [{'value': -5}], 'expected': -5}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.sum_tree(*args, **kwargs)
                else:
                    self.assertEqual(solution.sum_tree(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
