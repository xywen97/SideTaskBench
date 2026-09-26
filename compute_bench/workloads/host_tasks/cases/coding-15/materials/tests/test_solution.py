import unittest
import solution


class Tests(unittest.TestCase):
    def test_quotes_assignments_and_pipe(self):
        got=solution.parse_pipeline("A=1 echo 'a b' | grep b")
        self.assertEqual(got,[{'env':{'A':'1'},'argv':['echo','a b']},{'env':{},'argv':['grep','b']}])

    def test_comments(self):
        self.assertEqual(solution.parse_pipeline('echo x # ignored'),[{'env':{},'argv':['echo','x']}])

if __name__ == '__main__':
    unittest.main()
