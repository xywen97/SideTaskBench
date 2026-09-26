import unittest
import solution


class Tests(unittest.TestCase):
    def test_standard_hop_headers_removed(self):
        got=solution.merge_headers([('TE','trailers'),('Upgrade','websocket'),('X',' y ')], [('Keep-Alive','x')])
        self.assertEqual(got,[('x','y')])

    def test_singletons_use_last_update(self):
        got=solution.merge_headers([('Host','a')],[('host','b'),('HOST','c'),('Content-Length','2')])
        self.assertEqual(got,[('host','c'),('content-length','2')])

    def test_rejects_injection_and_bad_name(self):
        for pair in [(('Bad Name','x'),),(('X','a\nb'),)]:
            with self.subTest(pair=pair), self.assertRaises(ValueError): solution.merge_headers(pair,[])

    def test_no_mutation(self):
        base=[('X',' 1 ')]; updates=[('Y','2')]; solution.merge_headers(base,updates)
        self.assertEqual(base,[('X',' 1 ')]); self.assertEqual(updates,[('Y','2')])

if __name__ == '__main__':
    unittest.main()
