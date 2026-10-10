import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['123.456', '0.01', 'ROUND_HALF_UP'], '123.46'], [['2.5', '1', 'ROUND_HALF_EVEN'], '2'], [['2.5', '1', 'ROUND_HALF_UP'], '3'], [['1.009', '0.01', 'ROUND_DOWN'], '1.00'], [['-1.25', '0.1', 'ROUND_HALF_UP'], '-1.3']]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.decimal_quantize_rounding(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
