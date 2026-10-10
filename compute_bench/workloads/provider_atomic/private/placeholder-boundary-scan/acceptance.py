import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['Hello ${name}, your ${item} is ready'], [{'start': 6, 'end': 13, 'name': 'name'}, {'start': 20, 'end': 27, 'name': 'item'}]], [['cost $${price} for ${user}'], [{'start': 19, 'end': 26, 'name': 'user'}]], [['no placeholders'], []], [['${a}${b}'], [{'start': 0, 'end': 4, 'name': 'a'}, {'start': 4, 'end': 8, 'name': 'b'}]]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.placeholder_boundary_scan(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
