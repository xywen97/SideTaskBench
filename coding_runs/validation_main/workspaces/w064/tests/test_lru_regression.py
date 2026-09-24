import unittest

import solution


class CapacityValidationTests(unittest.TestCase):
    def test_rejects_bool(self):
        for bad in (True, False):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_rejects_non_positive(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_rejects_non_int(self):
        for bad in (2.0, "2", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_accepts_positive_int(self):
        self.assertEqual(len(solution.LRUCache(1)), 0)


class RecencyTests(unittest.TestCase):
    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "d"), "d")
        self.assertEqual(len(cache), 0)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(2)
        cache.put("n", None)
        cache.put("z", 0)
        self.assertIsNone(cache.get("n"))
        self.assertEqual(cache.get("z"), 0)
        self.assertTrue("n" in cache._items)
        self.assertEqual(len(cache), 2)

    def test_update_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # replace should refresh "a"
        cache.put("c", 3)  # evicts "b"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)

    def test_eviction_only_when_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)  # no premature eviction
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("a"))

    def test_read_refresh_changes_eviction_order(self):
        cache = solution.LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # "a" now most recently used
        cache.put("d", 4)  # evicts "b"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)


if __name__ == "__main__":
    unittest.main()
