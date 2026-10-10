import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[[[2, 3, 2], [3, 5, 7]], [23, 105]], [[[1], [4]], [1, 4]], [[[0, 0], [3, 5]], [0, 15]], [[[1, 2], [5, 7]], [16, 35]], [[[2, 3], [3, 4]], [11, 12]]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.crt_combine_residues(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
