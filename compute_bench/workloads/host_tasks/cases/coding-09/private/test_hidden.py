import unittest
import solution


class Tests(unittest.TestCase):
    def test_backslash_and_digest_case(self):
        got = solution.build_copy_plan('out/root', [{'path':'a\\b.txt','size':1,'sha256':'AB'*32}])
        self.assertEqual(got, [{'path':'a/b.txt','target':'out/root/a/b.txt','size':1,'sha256':'ab'*32}])

    def test_duplicate_after_normalization(self):
        e=[{'path':'a/b','size':1,'sha256':'0'*64},{'path':'a//b','size':1,'sha256':'1'*64}]
        with self.assertRaises(ValueError): solution.build_copy_plan('dst', e)

    def test_absolute_drive_size_and_digest(self):
        base={'size':1,'sha256':'0'*64}
        for path in ['/x','C:\\x']:
            with self.subTest(path=path), self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':path,**base}])
        for size in [-1, True, 1.5]:
            with self.subTest(size=size), self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':'x','size':size,'sha256':'0'*64}])
        with self.assertRaises(ValueError): solution.build_copy_plan('dst',[{'path':'x','size':1,'sha256':'x'}])

    def test_no_mutation(self):
        e=[{'path':'a','size':1,'sha256':'0'*64}]; before=[dict(e[0])]
        solution.build_copy_plan('dst',e); self.assertEqual(e,before)

if __name__ == '__main__':
    unittest.main()
