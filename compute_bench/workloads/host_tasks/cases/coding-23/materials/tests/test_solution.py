import unittest

import solution
from dispatch import Registry


class Base:
    pass


class Middle(Base):
    pass


class Leaf(Middle):
    pass


class Other:
    pass


class PublicTests(unittest.TestCase):
    def test_exact_class_wins(self):
        registry = Registry()
        solution.register(registry, Base, "base")
        solution.register(registry, Leaf, "leaf")
        self.assertEqual(solution.resolve(registry, Leaf), "leaf")

    def test_nearest_ancestor_wins(self):
        registry = Registry()
        solution.register(registry, Base, "base")
        solution.register(registry, Middle, "middle")

        class Direct(Middle):
            pass

        self.assertEqual(solution.resolve(registry, Direct), "middle")

    def test_unregistered_class_raises(self):
        registry = Registry()
        solution.register(registry, Base, "base")
        with self.assertRaises(LookupError):
            solution.resolve(registry, Other)

    def test_registry_is_shared_not_copied(self):
        registry = Registry()
        solution.register(registry, Base, "base")
        self.assertTrue(registry.registered(Base))


if __name__ == "__main__":
    unittest.main()
