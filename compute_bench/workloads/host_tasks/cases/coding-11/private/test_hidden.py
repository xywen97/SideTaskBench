import unittest
import solution


class Tests(unittest.TestCase):
    def test_defaults_are_fresh(self):
        a=solution.resolve_settings([]); b=solution.resolve_settings([]); a['tags'].append('x'); self.assertEqual(b['tags'],[])

    def test_unknown_and_invalid_values(self):
        for layer in [{'x':1},{'timeout':True},{'timeout':'nan'},{'retries':1.5},{'enabled':'yes'},{'tags':['x',1]}]:
            with self.subTest(layer=layer), self.assertRaises(ValueError): solution.resolve_settings([layer])

    def test_iterable_tags_and_reset(self):
        got=solution.resolve_settings([{'tags':(' a ','b','a')},{'tags':None}]); self.assertEqual(got['tags'],[])

    def test_no_mutation(self):
        layers=[{'tags':['a','b']}]; solution.resolve_settings(layers); self.assertEqual(layers,[{'tags':['a','b']}])

if __name__ == '__main__':
    unittest.main()
