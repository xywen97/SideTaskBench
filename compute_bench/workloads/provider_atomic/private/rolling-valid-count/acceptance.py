import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[[[1, None, 3, None, 5], 3], [1, 1, 2, 1, 2]], [[[None, None], 2], [0, 0]], [[[0, 0, 0], 1], [1, 1, 1]], [[[], 3], []], [[[None, 1, None], 2], [0, 1, 1]]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.rolling_valid_count(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
