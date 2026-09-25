import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_invalid_capacity_does_not_mutate(self):
        for capacity in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(capacity=capacity):
                entries = {"a": 1, "b": 2}
                with self.assertRaises(ValueError):
                    solution.update_cache(entries, "a", 3, capacity)
                self.assertEqual(list(entries.items()), [("a", 1), ("b", 2)])

    def test_order_and_fresh_result(self):
        for entries, key, value, capacity, expected in (
            ({"a": 1, "b": 2}, "a", 3, 2, [("b", 2), ("a", 3)]),
            ({"a": 1, "b": 2}, "c", 3, 2, [("b", 2), ("c", 3)]),
            ({"a": 1, "b": 2, "c": 3}, "d", 4, 1, [("d", 4)]),
        ):
            with self.subTest(entries=entries, key=key, capacity=capacity):
                before = list(entries.items())
                result = solution.update_cache(entries, key, value, capacity)
                self.assertIsInstance(result, dict)
                self.assertIsNot(result, entries)
                self.assertEqual(list(result.items()), expected)
                self.assertEqual(list(entries.items()), before)

    def test_private_cases(self):
        cases = [{'args': [{'a': 1, 'b': 2}, 'a', 3, 2], 'expected': {'b': 2, 'a': 3}, 'no_mutation': True}, {'args': [{'a': 1}, 'b', 2, 1], 'expected': {'b': 2}}, {'args': [{}, 'x', 1, 0], 'raises': 'ValueError'}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.update_cache(*args, **kwargs)
                else:
                    self.assertEqual(solution.update_cache(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
