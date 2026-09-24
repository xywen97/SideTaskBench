import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_get_refreshes_most_recently_used(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_miss_does_not_insert_or_refresh(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")
        self.assertEqual(len(cache), 1)

    def test_put_existing_refreshes_and_does_not_grow(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # refresh "a"
        cache.put("c", 3)   # evicts "b"
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)

    def test_falsey_values_are_cache_hits(self):
        cache = solution.LRUCache(2)
        cache.put("none", None)
        cache.put("zero", 0)
        self.assertIsNone(cache.get("none"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIn("none", cache._items)
        self.assertIn("zero", cache._items)

    def test_eviction_only_when_capacity_exceeded(self):
        cache = solution.LRUCache(3)
        for key in ("a", "b", "c"):
            cache.put(key, key)
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache.get("a"), "a")  # all still present
        cache.put("d", "d")  # now exceeds, evicts LRU "b"
        self.assertEqual(len(cache), 3)
        self.assertIsNone(cache.get("b"))

    def test_capacity_validation_rejects_bool_and_non_positive(self):
        for bad in (True, False, 0, -1, 1.0, "1"):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)
        self.assertEqual(len(solution.LRUCache(1)), 0)


if __name__ == "__main__":
    unittest.main()
