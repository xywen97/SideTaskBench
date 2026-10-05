import unittest

import solution
from dispatch import Registry, mro_chain


class A:
    pass


class B(A):
    pass


class C(A):
    pass


class D(B, C):
    pass


class Unrelated:
    pass


class HiddenTests(unittest.TestCase):
    def test_registration_order_does_not_matter(self):
        first = Registry()
        solution.register(first, A, "a")
        solution.register(first, D, "d")
        second = Registry()
        solution.register(second, D, "d")
        solution.register(second, A, "a")
        self.assertEqual(solution.resolve(first, D), "d")
        self.assertEqual(solution.resolve(second, D), "d")

    def test_nearest_base_wins_over_further_base(self):
        registry = Registry()
        solution.register(registry, A, "a")
        solution.register(registry, B, "b")
        solution.register(registry, C, "c")
        self.assertEqual(solution.resolve(registry, D), "b")

    def test_diamond_resolution(self):
        registry = Registry()
        solution.register(registry, C, "c")
        self.assertEqual(solution.resolve(registry, D), "c")

    def test_no_matching_registration_raises_lookup_error(self):
        registry = Registry()
        solution.register(registry, A, "a")
        with self.assertRaises(LookupError):
            solution.resolve(registry, Unrelated)

    def test_empty_registry_raises(self):
        with self.assertRaises(LookupError):
            solution.resolve(Registry(), A)

    def test_mro_chain_excludes_object(self):
        chain = mro_chain(D)
        self.assertEqual(chain, [D, B, C, A])
        self.assertNotIn(object, chain)

    def test_mro_chain_of_plain_class(self):
        self.assertEqual(mro_chain(A), [A])

    def test_registry_is_used_not_replaced(self):
        registry = Registry()
        solution.register(registry, A, "a")
        self.assertTrue(registry.registered(A))
        self.assertEqual(registry.handlers(), {A: "a"})

    def test_re_registration_replaces_handler(self):
        registry = Registry()
        solution.register(registry, A, "first")
        solution.register(registry, A, "second")
        self.assertEqual(solution.resolve(registry, A), "second")

    def test_handler_values_may_be_any_object(self):
        registry = Registry()
        marker = object()
        solution.register(registry, A, marker)
        self.assertIs(solution.resolve(registry, A), marker)


if __name__ == "__main__":
    unittest.main()
