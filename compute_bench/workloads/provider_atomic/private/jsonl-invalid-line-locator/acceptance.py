import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['{"a":1}\n{invalid\n{"b":2}\n'], [2]], [['{"a":1}\n\n[1,\n{"c":3}\n'], [3]], [['x\n\ny\n'], [1, 3]], [[''], []], [['1\n"s"\nnull\n{'], [4]]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.jsonl_invalid_line_locator(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
