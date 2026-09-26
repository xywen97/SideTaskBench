import unittest
import solution


class Tests(unittest.TestCase):
    def test_deduplicates_and_sorts(self):
        self.assertEqual(solution.stable_batches({'z':['a','a'],'a':[]}),[['a'],['z']])

    def test_cycle_selected_and_unselected(self):
        graph={'a':['b'],'b':['a'],'x':[]}
        with self.assertRaises(ValueError): solution.stable_batches(graph)
        self.assertEqual(solution.stable_batches(graph,['x']),[['x']])

    def test_unknown_and_invalid(self):
        with self.assertRaises(ValueError): solution.stable_batches({'a':[]},['x'])
        with self.assertRaises(ValueError): solution.stable_batches({1:[]})

    def test_no_mutation(self):
        graph={'a':['b'],'b':[]}; solution.stable_batches(graph); self.assertEqual(graph,{'a':['b'],'b':[]})

if __name__ == '__main__':
    unittest.main()
