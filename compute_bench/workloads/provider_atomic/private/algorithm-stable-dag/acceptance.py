import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [{'ship': ['build'], 'build': ['fetch'], 'lint': []}], 'expected': ['fetch', 'build', 'lint', 'ship'], 'no_mutation': True}, {'args': [{'a': ['b'], 'b': ['a']}], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.stable_schedule(*args, **kwargs)
                else:
                    self.assertEqual(solution.stable_schedule(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
