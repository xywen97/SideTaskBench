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
    def test_update_refreshes_order(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update should mark "a" most recently used
        cache.put("c", 3)   # should evict "b"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(len(cache), 2)

    def test_update_does_not_evict_extra(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("b", 20)  # replace, must not evict "a"
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 20)
        self.assertEqual(len(cache), 2)

    def test_miss_returns_default_without_inserting(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("x"))
        self.assertEqual(cache.get("x", "d"), "d")
        self.assertEqual(len(cache), 0)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertIsNone(cache.get("none"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIs(cache.get("false"), False)

    def test_eviction_only_when_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)  # at capacity, no eviction
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("a"))

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 2.0, "2", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_read_refreshes_multiple(self):
        cache = solution.LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.get("b")
        cache.put("d", 4)  # evicts "c"
        self.assertIsNone(cache.get("c"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)


if __name__ == "__main__":
    unittest.main()
