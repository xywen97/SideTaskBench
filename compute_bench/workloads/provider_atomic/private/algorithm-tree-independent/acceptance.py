import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_leaf_can_omit_children(self):
        for node in ({"weight": 7}, {"weight": 7, "children": []}):
            with self.subTest(node=node):
                before = copy.deepcopy(node)
                self.assertEqual(solution.max_tree_weight(node), 7)
                self.assertEqual(node, before)

    def test_private_cases(self):
        cases = [{'args': [{'weight': 5, 'children': [{'weight': 4}, {'weight': 3, 'children': [{'weight': 10}]}]}], 'expected': 15, 'no_mutation': True}, {'args': [{'weight': 0, 'children': []}], 'expected': 0}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.max_tree_weight(*args, **kwargs)
                else:
                    self.assertEqual(solution.max_tree_weight(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
