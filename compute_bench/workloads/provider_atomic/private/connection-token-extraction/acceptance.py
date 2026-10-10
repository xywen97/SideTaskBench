import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['keep-alive, Upgrade'], ['keep-alive', 'Upgrade']], [['  close  '], ['close']], [['a,b ,  c'], ['a', 'b', 'c']], [['Upgrade'], ['Upgrade']]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.connection_token_extraction(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
