import unittest

from solution import nthroot_mod


class HiddenTests(unittest.TestCase):
    def assertRoots(self, a, n, modulus, expected):
        roots = nthroot_mod(a, n, modulus, all_roots=True)
        self.assertEqual(roots, expected)
        self.assertEqual(roots, sorted(set(roots)))
        self.assertTrue(all(pow(root, n, modulus) == a % modulus for root in roots))
        self.assertEqual(nthroot_mod(a, n, modulus), roots[0] if roots else None)

    def test_zero_roots_over_prime_powers(self):
        self.assertRoots(0, 7, 100, list(range(0, 100, 10)))
        self.assertRoots(0, 3, 81, [0, 9, 18, 27, 36, 45, 54, 63, 72])

    def test_crt_combines_all_local_roots(self):
        self.assertRoots(1, 2, 72, [1, 17, 19, 35, 37, 53, 55, 71])
        self.assertRoots(9, 2, 100, [3, 47, 53, 97])

    def test_negative_and_large_a_are_normalized(self):
        expected = nthroot_mod(4, 3, 35, all_roots=True)
        self.assertEqual(nthroot_mod(4 + 35 * 20, 3, 35, all_roots=True), expected)
        self.assertEqual(nthroot_mod(4 - 35 * 20, 3, 35, all_roots=True), expected)

    def test_large_composite_does_not_scan_full_modulus(self):
        modulus = (9967 ** 4) * (9973 ** 5)
        roots = nthroot_mod(1, 5, modulus, all_roots=True)
        self.assertEqual(roots, [1])

    def test_three_prime_power_components(self):
        modulus = (2 ** 7) * (3 ** 4) * (5 ** 3)
        expected = [value for value in range(modulus)
                    if pow(value, 3, modulus) == 17 % modulus]
        self.assertRoots(17, 3, modulus, expected)

    def test_validation(self):
        for args in ((1, 0, 7), (1, 2, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                nthroot_mod(*args)
        with self.assertRaises(TypeError):
            nthroot_mod(True, 2, 7)


if __name__ == "__main__":
    unittest.main()
