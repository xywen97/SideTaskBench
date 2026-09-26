import unittest
import solution


class Tests(unittest.TestCase):
    def test_normalizes_and_orders(self):
        got=solution.plan_archive([{'name':'a\\b.txt','size':2,'is_dir':False},{'name':'a','size':0,'is_dir':True}],2)
        self.assertEqual([x['name'] for x in got],['a','a/b.txt'])

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'../x','size':1,'is_dir':False}],2)

if __name__ == '__main__':
    unittest.main()
