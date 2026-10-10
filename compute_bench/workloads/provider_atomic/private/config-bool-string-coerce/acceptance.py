import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[[{'enabled': 'true', 'debug': 'false', 'count': '5'}], {'enabled': True, 'debug': False, 'count': '5'}], [[{'a': 'True', 'b': 'FALSE', 'c': True, 'd': 0, 'e': ''}], {'a': 'True', 'b': 'FALSE', 'c': True, 'd': 0, 'e': ''}], [[{'x': 'true', 'y': None}], {'x': True, 'y': None}]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.config_bool_string_coerce(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
