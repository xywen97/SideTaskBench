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
    def test_put_existing_refreshes(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", 0), 0)
        self.assertEqual(len(cache), 0)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(2)
        cache.put("none", None)
        cache.put("zero", 0)
        self.assertIn("none", cache._items)
        self.assertIsNone(cache.get("none", "sentinel"))
        self.assertEqual(cache.get("zero", "sentinel"), 0)

    def test_eviction_only_when_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        cache.put("a", 1)
        self.assertEqual(len(cache), 2)
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)

    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 2.0, "2"):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)


if __name__ == "__main__":
    unittest.main()
