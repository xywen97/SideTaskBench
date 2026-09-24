import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_insert_and_get(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(len(cache), 1)
    def test_read_refreshes(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)


class RegressionTests(unittest.TestCase):
    def test_update_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update should make "a" most recently used
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(len(cache), 2)

    def test_update_does_not_evict(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 100)
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache.get("a"), 100)
        self.assertEqual(cache.get("b"), 2)

    def test_miss_returns_default_and_does_not_insert(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("b", "fallback"), "fallback")
        self.assertEqual(len(cache), 1)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(4)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        cache.put("empty", "")
        for key, expected in (
            ("none", None),
            ("zero", 0),
            ("false", False),
            ("empty", ""),
        ):
            self.assertEqual(cache.get(key, "MISS"), expected)
        self.assertEqual(len(cache), 4)

    def test_eviction_order_is_least_recently_used(self):
        cache = solution.LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")          # order: b, c, a
        cache.put("d", 4)       # evicts b
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(cache.get("d"), 4)

    def test_invalid_capacity_raises_value_error(self):
        for bad in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(capacity=bad):
                with self.assertRaises(ValueError):
                    solution.LRUCache(bad)

    def test_capacity_one(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(len(cache), 1)


if __name__ == "__main__":
    unittest.main()
