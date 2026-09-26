import unittest
import solution


class Tests(unittest.TestCase):
    def test_batches_and_dependency_only_nodes(self):
        self.assertEqual(solution.stable_batches({'build':['lint','test'],'test':['compile']}),[['compile','lint'],['test'],['build']])

    def test_target_closure(self):
        self.assertEqual(solution.stable_batches({'a':['b'],'b':[],'x':[]},['a']),[['b'],['a']])

if __name__ == '__main__':
    unittest.main()
