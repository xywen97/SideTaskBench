import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [{'args': [{'a': {'items': [1], 'next': 'b'}, 'b': {'items': [], 'next': 'c'}, 'c': {'items': [2], 'next': None}}, 'a'], 'expected': [1, 2], 'no_mutation': True}, {'args': [{'a': {'items': [], 'next': 'a'}}, 'a'], 'raises': 'ValueError'}, {'args': [{}, None], 'expected': []}, {'args': [{}, 'missing'], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.collect_pages(*args, **kwargs)
                else:
                    self.assertEqual(solution.collect_pages(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
