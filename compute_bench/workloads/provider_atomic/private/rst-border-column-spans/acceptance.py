import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['+-----+-----+-----+'], {'column_count': 3, 'column_widths': [5, 5, 5]}], [['+--+------+'], {'column_count': 2, 'column_widths': [2, 6]}], [['+===+'], {'column_count': 1, 'column_widths': [3]}], [['+-+--+---+'], {'column_count': 3, 'column_widths': [1, 2, 3]}]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.rst_border_column_spans(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
