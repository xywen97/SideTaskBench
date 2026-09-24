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
        # Replacing "a" must mark it most recently used.
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("false", False)
        cache.put("zero", 0)
        self.assertIsNone(cache.get("none", "sentinel"))
        self.assertIs(cache.get("false", "sentinel"), False)
        self.assertEqual(cache.get("zero", "sentinel"), 0)
        self.assertEqual(len(cache), 3)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        self.assertEqual(cache.get("missing"), None)
        self.assertEqual(cache.get("missing", 42), 42)
        self.assertEqual(len(cache), 0)

    def test_eviction_only_when_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        cache.put("b", 20)  # replace, no eviction
        self.assertEqual(len(cache), 2)
        # "b" is now most recently used, so "a" is the LRU entry.
        cache.put("c", 3)  # exceeded: evict LRU ("a")
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 20)
        self.assertEqual(cache.get("c"), 3)

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 1.5, "2", None):
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
