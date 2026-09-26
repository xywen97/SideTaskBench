import unittest
import solution


class Tests(unittest.TestCase):
    def test_quoted_pipe_and_last_assignment(self):
        got=solution.parse_pipeline("A=1 A=2 printf 'x|y'"); self.assertEqual(got,[{'env':{'A':'2'},'argv':['printf','x|y']}])

    def test_empty_and_assignment_only(self):
        for text in ['', '| x', 'x || y', 'A=1']:
            with self.subTest(text=text), self.assertRaises(ValueError): solution.parse_pipeline(text)

    def test_invalid_and_late_assignment(self):
        for text in ['1A=x cmd','cmd A=x']:
            with self.subTest(text=text), self.assertRaises(ValueError): solution.parse_pipeline(text)

    def test_escapes(self):
        self.assertEqual(solution.parse_pipeline(r'echo a\ b')[0]['argv'],['echo','a b'])

if __name__ == '__main__':
    unittest.main()
