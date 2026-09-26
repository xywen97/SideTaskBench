import unittest
import solution


class Tests(unittest.TestCase):
    def test_layers_and_types(self):
        got=solution.resolve_settings([{'timeout':'2.5','tags':'a, b,a'},{'enabled':'false','retries':'0'}])
        self.assertEqual(got,{'timeout':2.5,'retries':0,'enabled':False,'tags':['a','b']})

    def test_none_resets_default(self):
        self.assertEqual(solution.resolve_settings([{'timeout':2},{'timeout':None}])['timeout'],5.0)

    def test_strict_value_domains(self):
        self.assertTrue(solution.resolve_settings([{'enabled':'yes'}])['enabled'])
        self.assertFalse(solution.resolve_settings([{'enabled':'OFF'}])['enabled'])
        for layer in ({'enabled':'maybe'}, {'timeout':'nan'}, {'retries':1.5}, {'tags':['x',1]}):
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                solution.resolve_settings([layer])

if __name__ == '__main__':
    unittest.main()
