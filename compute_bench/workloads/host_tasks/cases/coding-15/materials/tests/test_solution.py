import unittest
import solution


class Tests(unittest.TestCase):
    def test_quotes_assignments_and_pipe(self):
        got=solution.parse_pipeline("A=1 echo 'a b' | grep b")
        self.assertEqual(got,[{'env':{'A':'1'},'argv':['echo','a b']},{'env':{},'argv':['grep','b']}])

    def test_comments(self):
        self.assertEqual(solution.parse_pipeline('echo x # ignored'),[{'env':{},'argv':['echo','x']}])

    def test_rejects_empty_stages_and_assignment_only(self):
        for text in ('', 'x || y', 'A=1'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                solution.parse_pipeline(text)

if __name__ == '__main__':
    unittest.main()
