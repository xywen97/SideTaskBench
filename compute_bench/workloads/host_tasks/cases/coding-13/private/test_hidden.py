import unittest
import solution


class Tests(unittest.TestCase):
    def test_all_windows_and_generator(self):
        got=solution.rolling_summary((x for x in [1,2,3]),2); self.assertEqual([x['mean'] for x in got],[1.5,2.5])

    def test_invalid_dimensions(self):
        for args in [([1],0,1),([1],2,1),([1],1,0),([1],1,2),([1],True,1)]:
            with self.subTest(args=args), self.assertRaises(ValueError): solution.rolling_summary(*args)

    def test_invalid_values(self):
        for value in [True,float('nan'),float('inf'),'1']:
            with self.subTest(value=value), self.assertRaises(ValueError): solution.rolling_summary([value],1)

    def test_no_mutation(self):
        values=[1,None,2]; solution.rolling_summary(values,2); self.assertEqual(values,[1,None,2])

if __name__ == '__main__':
    unittest.main()
