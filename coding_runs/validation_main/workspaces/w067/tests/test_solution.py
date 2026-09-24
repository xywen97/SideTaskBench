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
    def test_capacity_must_be_positive_int_excluding_bool(self):
        for bad in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(capacity=bad):
                with self.assertRaises(ValueError):
                    solution.LRUCache(bad)

    def test_miss_returns_default_without_inserting(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", 42), 42)
        self.assertEqual(len(cache), 0)

    def test_put_replace_refreshes_recency(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # replace "a", mark most recently used
        cache.put("c", 3)   # should evict "b"
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(len(cache), 2)

    def test_replace_does_not_consume_extra_capacity(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        cache.put("a", 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("a"), 2)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertIsNone(cache.get("none", "sentinel"))
        self.assertEqual(cache.get("zero", "sentinel"), 0)
        self.assertEqual(cache.get("false", "sentinel"), False)

    def test_eviction_only_when_capacity_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)  # not exceeded, no eviction
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)


if __name__ == "__main__":
    unittest.main()
