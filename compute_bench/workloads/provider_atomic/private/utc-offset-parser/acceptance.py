import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['-05:30'], {'hours': -5, 'minutes': -30, 'total_minutes': -330}], [['+02:00'], {'hours': 2, 'minutes': 0, 'total_minutes': 120}], [['+00:45'], {'hours': 0, 'minutes': 45, 'total_minutes': 45}], [['-00:15'], {'hours': 0, 'minutes': -15, 'total_minutes': -15}], [['+14:00'], {'hours': 14, 'minutes': 0, 'total_minutes': 840}]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.utc_offset_parser(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
