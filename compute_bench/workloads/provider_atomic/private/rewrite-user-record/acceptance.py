import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [{'user_id': 'u1', 'full_name': ' Ada ', 'active': 1, 'x': 2}], 'expected': {'id': 'u1', 'display_name': 'Ada', 'active': True}, 'no_mutation': True}, {'args': [{'user_id': 'u2', 'full_name': 'Lin', 'active': 0}], 'expected': {'id': 'u2', 'display_name': 'Lin', 'active': False}}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.normalize_user(*args, **kwargs)
                else:
                    self.assertEqual(solution.normalize_user(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
