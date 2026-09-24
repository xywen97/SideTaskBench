import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_update_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update existing key -> most recently used
        cache.put("c", 3)   # should evict "b", not "a"
        self.assertEqual(cache.get("a"), 10)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), 3)

    def test_update_existing_does_not_grow(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        cache.put("a", 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("a"), 2)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "d"), "d")
        self.assertEqual(len(cache), 1)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        cache.put("empty", "")
        self.assertEqual(len(cache), 3)
        # none/zero/false/empty were inserted; "none" should have been evicted
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIs(cache.get("false"), False)
        self.assertEqual(cache.get("empty"), "")
        self.assertEqual(len(cache), 3)

    def test_falsey_none_stored_is_a_hit_not_default(self):
        cache = solution.LRUCache(1)
        cache.put("k", None)
        sentinel = object()
        self.assertIsNone(cache.get("k", sentinel))
        self.assertEqual(len(cache), 1)

    def test_eviction_only_when_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("a"))

    def test_capacity_validation(self):
        for bad in (0, -1, 1.5, True, False, "3", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_read_refreshes_under_repeated_use(self):
        cache = solution.LRUCache(3)
        for k in ("a", "b", "c"):
            cache.put(k, k)
        cache.get("a")
        cache.get("b")
        cache.put("d", "d")  # evicts "c"
        self.assertIsNone(cache.get("c"))
        self.assertEqual(cache.get("a"), "a")
        self.assertEqual(cache.get("b"), "b")


if __name__ == "__main__":
    unittest.main()
