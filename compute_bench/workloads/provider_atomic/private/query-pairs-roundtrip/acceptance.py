import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[[[['key', 'value'], ['a', 'b=c']]], [['key', 'value'], ['a', 'b=c']]], [[[['q', 'x&y'], ['sp ace', '50%'], ['empty', '']]], [['q', 'x&y'], ['sp ace', '50%'], ['empty', '']]], [[[['k', 'a+b'], ['k', 'é']]], [['k', 'a+b'], ['k', 'é']]], [[[['a b', 'c/d?e#f']]], [['a b', 'c/d?e#f']]]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.query_pairs_roundtrip(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
