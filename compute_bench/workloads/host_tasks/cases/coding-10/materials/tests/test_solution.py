import unittest
import solution


class Tests(unittest.TestCase):
    def test_case_insensitive_replacement_and_append(self):
        got=solution.merge_headers([('Content-Type',' text/plain '),('X-A','1')],[('content-type','application/json'),('X-A','2')])
        self.assertEqual(got,[('x-a','1'),('content-type','application/json'),('x-a','2')])

    def test_strips_hop_headers(self):
        self.assertEqual(solution.merge_headers([('Connection','X-Trace'),('X-Trace','secret'),('X-End','ok')],[]),[('x-end','ok')])

    def test_rejects_invalid_names_and_injection(self):
        for pair in [(('Bad Name','x'),), (('X-Test','a\nb'),)]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                solution.merge_headers(pair, [])

if __name__ == '__main__':
    unittest.main()
