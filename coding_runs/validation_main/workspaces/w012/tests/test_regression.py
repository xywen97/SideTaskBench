import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_put_of_existing_key_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # replacement, must become most recently used
        cache.put("c", 3)   # evicts "b", not "a"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(len(cache), 2)

    def test_get_miss_does_not_insert_or_evict(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(len(cache), 1)
        # "a" still present and still the only entry, so a new put evicts it.
        self.assertEqual(cache.get("missing", 42), 42)
        self.assertEqual(len(cache), 1)
        cache.put("b", 2)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(2)
        for value in (None, 0, False, "", []):
            cache.put("k", value)
            self.assertIn("k", cache._items)
            self.assertIs(cache.get("k"), value)
            self.assertEqual(len(cache), 1)

    def test_len_and_eviction_order(self):
        cache = solution.LRUCache(3)
        for key in "abc":
            cache.put(key, key)
        cache.get("a")           # order: b, c, a
        cache.get("b")           # order: c, a, b
        cache.put("d", "d")      # evicts c -> a, b, d
        self.assertIsNone(cache.get("c"))
        self.assertEqual(len(cache), 3)
        self.assertEqual(set(cache._items), {"a", "b", "d"})

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 1.5, "2", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)
        self.assertEqual(len(solution.LRUCache(1)), 0)


if __name__ == "__main__":
    unittest.main()
