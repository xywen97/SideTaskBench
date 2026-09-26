import unittest
import solution


class Tests(unittest.TestCase):
    def test_size_limit_and_directory_size(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':3,'is_dir':False}],2)
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'d','size':1,'is_dir':True}],2)

    def test_duplicate_and_file_parent(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':0,'is_dir':True},{'name':'x/','size':0,'is_dir':True}],0)
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x','size':1,'is_dir':False},{'name':'x/y','size':1,'is_dir':False}],2)

    def test_descendant_before_file_conflict(self):
        with self.assertRaises(ValueError): solution.plan_archive([{'name':'x/y','size':1,'is_dir':False},{'name':'x','size':1,'is_dir':False}],2)

    def test_invalid_limit_and_no_mutation(self):
        for limit in [-1,True,1.5]:
            with self.subTest(limit=limit), self.assertRaises(ValueError): solution.plan_archive([],limit)
        m=[{'name':'x','size':1,'is_dir':False}]; solution.plan_archive(m,1); self.assertEqual(m,[{'name':'x','size':1,'is_dir':False}])

if __name__ == '__main__':
    unittest.main()
