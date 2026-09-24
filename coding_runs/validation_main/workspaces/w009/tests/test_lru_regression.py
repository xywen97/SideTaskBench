import unittest

import solution


class LRURegressionTests(unittest.TestCase):
    def test_update_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update "a" -> now most recently used
        cache.put("c", 3)   # should evict "b", not "a"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)

    def test_read_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")
        self.assertEqual(len(cache), 1)
        cache.put("b", 2)
        cache.put("c", 3)  # "a" is still LRU and must be evicted
        self.assertIsNone(cache.get("a"))

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        for key, value in (("none", None), ("zero", 0), ("false", False), ("empty", "")):
            cache.put(key, value)
        self.assertIsNone(cache.get("none"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIs(cache.get("false"), False)
        self.assertEqual(cache.get("empty"), "")
        # A missing key is still distinguishable from a stored None.
        sentinel = object()
        self.assertIs(cache.get("absent", sentinel), sentinel)

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 1.0, "2", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_eviction_only_on_overflow(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        cache.put("a", 3)  # replacement must not grow the cache
        self.assertEqual(len(cache), 2)


if __name__ == "__main__":
    unittest.main()
