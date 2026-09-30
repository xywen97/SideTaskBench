import unittest

from solution import nthroot_mod


class PublicTests(unittest.TestCase):
    def test_prime_modulus(self):
        roots = nthroot_mod(4, 2, 7, all_roots=True)
        self.assertEqual(roots, [2, 5])
        self.assertTrue(all(pow(root, 2, 7) == 4 for root in roots))

    def test_no_solution(self):
        self.assertEqual(nthroot_mod(3, 2, 7, all_roots=True), [])
        self.assertIsNone(nthroot_mod(3, 2, 7))

    def test_squarefree_composite(self):
        self.assertEqual(nthroot_mod(4, 2, 15, all_roots=True), [2, 7, 8, 13])


if __name__ == "__main__":
    unittest.main()
