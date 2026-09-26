import unittest
import solution


class Tests(unittest.TestCase):
    def test_normalizes_and_sorts(self):
        d = 'A' * 64
        got = solution.build_copy_plan('dst', [{'path':'b.txt','size':2,'sha256':d}, {'path':'a/./x','size':0,'sha256':d}])
        self.assertEqual([x['path'] for x in got], ['a/x','b.txt'])
        self.assertEqual(got[0]['target'], 'dst/a/x')

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError): solution.build_copy_plan('dst', [{'path':'../x','size':1,'sha256':'0'*64}])

    def test_backslashes_duplicates_and_strict_metadata(self):
        got = solution.build_copy_plan('dst', [{'path':'a\\b','size':1,'sha256':'AB'*32}])
        self.assertEqual(got[0]['path'], 'a/b')
        self.assertEqual(got[0]['sha256'], 'ab'*32)
        with self.assertRaises(ValueError):
            solution.build_copy_plan('dst', [{'path':'a/b','size':1,'sha256':'0'*64}, {'path':'a//b','size':1,'sha256':'1'*64}])
        for size in (True, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                solution.build_copy_plan('dst', [{'path':'x','size':size,'sha256':'0'*64}])

if __name__ == '__main__':
    unittest.main()
