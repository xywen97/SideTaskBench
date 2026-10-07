import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_private_cases(self):
        cases = [
            {"args": [{"build": ["fetch"], "test": ["build"], "lint": [], "fetch": []}, ["test"]], "expected": ["build", "fetch", "test"], "no_mutation": True},
            {"args": [{"a": ["b", "c"], "b": ["d"], "c": [], "d": []}, ["a"]], "expected": ["a", "b", "c", "d"], "no_mutation": True},
            {"args": [{"x": [], "y": []}, ["y"]], "expected": ["y"], "no_mutation": True},
            {"args": [{"a": [], "b": []}, ["a", "b"]], "expected": ["a", "b"], "no_mutation": True},
            {"args": [{"a": []}, ["z"]], "raises": "ValueError"},
        ]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.reachable_nodes(*args, **kwargs)
                else:
                    self.assertEqual(solution.reachable_nodes(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
