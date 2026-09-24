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
    def test_capacity_validation(self):
        for bad in (0, -1, True, False, 1.0, "1", None):
            with self.assertRaises(ValueError):
                solution.LRUCache(bad)
        self.assertIsInstance(solution.LRUCache(1), solution.LRUCache)

    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("x"))
        self.assertEqual(cache.get("x", 42), 42)
        self.assertEqual(len(cache), 0)

    def test_put_update_refreshes_and_no_extra_eviction(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)  # update -> most recent, no eviction
        self.assertEqual(len(cache), 2)
        cache.put("c", 3)  # evicts b (least recent), keeps a
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)
        self.assertEqual(cache.get("c"), 3)

    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(3)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        self.assertEqual(len(cache), 3)
        self.assertIsNone(cache.get("none"))
        self.assertEqual(cache.get("zero"), 0)
        self.assertIs(cache.get("false"), False)
        cache.get("none")  # refresh None entry
        cache.put("new", 1)  # evicts zero (least recently used)
        self.assertEqual(cache.get("zero", "gone"), "gone")
        self.assertIsNone(cache.get("none"))
        self.assertIs(cache.get("false"), False)

    def test_evict_only_when_exceeded(self):
        cache = solution.LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        self.assertEqual(len(cache), 3)
        cache.put("d", 4)  # now exceeds -> evict a
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache.get("a", "gone"), "gone")


if __name__ == "__main__":
    unittest.main()
