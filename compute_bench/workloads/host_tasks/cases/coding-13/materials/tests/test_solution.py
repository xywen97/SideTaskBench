import unittest
import solution


class Tests(unittest.TestCase):
    def test_missing_values_and_threshold(self):
        got=solution.rolling_summary([1,None,3,5],3,2)
        self.assertEqual(got,[{'start':0,'count':2,'mean':2.0,'min':1,'max':3},{'start':1,'count':2,'mean':4.0,'min':3,'max':5}])

    def test_below_threshold(self):
        self.assertEqual(solution.rolling_summary([None,2],2,2)[0]['mean'],None)

if __name__ == '__main__':
    unittest.main()
