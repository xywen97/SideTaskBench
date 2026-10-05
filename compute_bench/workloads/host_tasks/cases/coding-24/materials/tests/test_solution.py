import unittest

from solution import Cache


class PublicTests(unittest.TestCase):
    def test_memoises_repeated_lookups(self):
        cache = Cache()
        calls = []
        produce = lambda: calls.append(1) or "value"

        self.assertEqual(cache.compute("a", produce=produce), "value")
        self.assertEqual(cache.compute("a", produce=produce), "value")
        self.assertEqual(len(calls), 1)
        self.assertEqual(cache.calls, 1)

    def test_invalidate_forces_recompute(self):
        cache = Cache()
        values = iter(["first", "second"])
        produce = lambda: next(values)

        self.assertEqual(cache.compute("a", produce=produce), "first")
        cache.invalidate("a")
        self.assertEqual(cache.compute("a", produce=produce), "second")

    def test_direct_dependent_is_refreshed(self):
        cache = Cache()
        cache.compute("base", produce=lambda: 1)
        cache.compute("derived", sources=("base",), produce=lambda: "old")

        cache.invalidate("base")
        self.assertFalse(cache.store.has("derived"))
        self.assertEqual(cache.compute("derived", sources=("base",), produce=lambda: "new"), "new")

    def test_self_dependency_is_rejected(self):
        cache = Cache()
        with self.assertRaises(KeyError):
            cache.store.put("a", 1, ("a",))

    def test_missing_without_produce_is_an_error(self):
        cache = Cache()
        with self.assertRaises(ValueError):
            cache.compute("absent")


if __name__ == "__main__":
    unittest.main()
