import copy
import json
import unittest
import solution


def plain(value):
    # Tuples and lists are interchangeable in the public contract.
    return json.loads(json.dumps(value))


class Acceptance(unittest.TestCase):
    def test_cases_without_mutation(self):
        cases = [[['a,b\n"x,y",z\n'], ['a,b', '"x,y",z']], [['id,note\n1,"line one\nline two"\n2,plain\n'], ['id,note', '1,"line one\nline two"', '2,plain']], [['a,"say ""hi"""\nb,c'], ['a,"say ""hi"""', 'b,c']], [['only'], ['only']]]
        for index, (args, expected) in enumerate(cases):
            with self.subTest(index=index, args=args):
                args = copy.deepcopy(args)
                before = copy.deepcopy(args)
                result = solution.csv_quoted_record_splitter(*args)
                self.assertEqual(plain(result), expected)
                self.assertEqual(args, before)
