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
        cache.put("a", 10)  # replace should mark "a" most recently used
        cache.put("c", 3)   # "b" is now least recently used and evicted
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(len(cache), 2)

    def test_updating_existing_key_does_not_grow(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("a", 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("a"), 2)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertIsNone(cache.get("none", "MISS"))
        self.assertEqual(cache.get("zero", "MISS"), 0)
        self.assertIs(cache.get("false", "MISS"), False)
        self.assertEqual(cache.get("absent", "MISS"), "MISS")
        self.assertEqual(len(cache), 3)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "d"), "d")
        self.assertEqual(len(cache), 0)

    def test_eviction_only_when_capacity_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)  # at capacity, nothing evicted
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)
        self.assertIsNone(cache.get("a"))

    def test_invalid_capacity_raises_value_error(self):
        for bad in (0, -1, 1.0, "2", None, True, False):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)

    def test_valid_capacity_accepts_plain_int(self):
        self.assertEqual(len(solution.LRUCache(1)), 0)


if __name__ == "__main__":
    unittest.main()
