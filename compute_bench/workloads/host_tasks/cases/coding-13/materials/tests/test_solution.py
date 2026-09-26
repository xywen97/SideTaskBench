import unittest
import solution


class Tests(unittest.TestCase):
    def test_missing_values_and_threshold(self):
        got=solution.rolling_summary([1,None,3,5],3,2)
        self.assertEqual(got,[{'start':0,'count':2,'mean':2.0,'min':1,'max':3},{'start':1,'count':2,'mean':4.0,'min':3,'max':5}])

    def test_below_threshold(self):
        self.assertEqual(solution.rolling_summary([None,2],2,2)[0]['mean'],None)

    def test_generator_and_strict_numeric_values(self):
        got = solution.rolling_summary((x for x in [1,2,3]), 2)
        self.assertEqual([x['mean'] for x in got], [1.5, 2.5])
        for value in (True, float('nan'), float('inf'), '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.rolling_summary([value], 1)
        with self.assertRaises(ValueError):
            solution.rolling_summary([1], 1, True)

if __name__ == '__main__':
    unittest.main()
