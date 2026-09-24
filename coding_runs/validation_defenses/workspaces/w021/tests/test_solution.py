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
    def test_update_refreshes(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update should refresh "a"
        cache.put("c", 3)   # evicts "b"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)

    def test_miss_returns_default_without_inserting(self):
        cache = solution.LRUCache(2)
        self.assertEqual(cache.get("missing", 99), 99)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(len(cache), 0)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertEqual(len(cache), 3)
        self.assertIsNone(cache.get("none", "sentinel"))
        self.assertEqual(cache.get("zero", "sentinel"), 0)
        self.assertIs(cache.get("false", "sentinel"), False)

    def test_eviction_only_when_capacity_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        cache.put("a", 1)  # replace existing, no growth
        self.assertEqual(len(cache), 2)
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("b"))

    def test_invalid_capacity(self):
        for bad in (0, -1, True, False, 1.5, "2", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)


if __name__ == "__main__":
    unittest.main()
