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
    def test_put_existing_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        # Replacing "a" must mark it most recently used.
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(len(cache), 2)

    def test_put_existing_does_not_evict(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        cache.put("a", 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("a"), 2)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")
        self.assertEqual(len(cache), 1)
        # The miss must not have disturbed "a"'s recency relative to order.
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertIsNone(cache.get("none"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIs(cache.get("false"), False)
        self.assertEqual(len(cache), 3)

    def test_eviction_order_is_least_recently_used(self):
        cache = solution.LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.get("b")
        cache.put("d", 4)  # evicts "c"
        self.assertIsNone(cache.get("c"))
        self.assertEqual([cache.get(k) for k in ("a", "b", "d")], [1, 2, 4])
        self.assertEqual(len(cache), 3)

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 1.0, "1", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)
        self.assertEqual(len(solution.LRUCache(1)), 0)


if __name__ == "__main__":
    unittest.main()
