import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [{'a': {'value': 2, 'next': 'b'}, 'b': {'value': 3, 'next': None}}, 'a', 5], 'expected': {'tokens': ['a', 'b'], 'total': 5}, 'no_mutation': True}, {'args': [{'a': {'value': 6, 'next': None}}, 'a', 5], 'raises': 'ValueError'}, {'args': [{}, None, 0], 'expected': {'tokens': [], 'total': 0}}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.bounded_chain(*args, **kwargs)
                else:
                    self.assertEqual(solution.bounded_chain(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
