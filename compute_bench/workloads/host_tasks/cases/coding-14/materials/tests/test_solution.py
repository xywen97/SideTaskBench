import unittest
import solution


class Tests(unittest.TestCase):
    def test_batches_and_dependency_only_nodes(self):
        self.assertEqual(solution.stable_batches({'build':['lint','test'],'test':['compile']}),[['compile','lint'],['test'],['build']])

    def test_target_closure(self):
        self.assertEqual(solution.stable_batches({'a':['b'],'b':[],'x':[]},['a']),[['b'],['a']])

    def test_cycles_are_invalid(self):
        with self.assertRaises(ValueError): solution.stable_batches({'a':['b'],'b':['a']})
        with self.assertRaises(ValueError): solution.stable_batches({'a':[]}, ['missing'])
        with self.assertRaises(ValueError): solution.stable_batches({1:[]})

if __name__ == '__main__':
    unittest.main()
