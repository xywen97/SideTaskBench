import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_update_refreshes(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 9)
        cache.put("c", 3)
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache.get("a"), 9)
        self.assertIsNone(cache.get("b"))
    def test_miss_does_not_insert(self):
        cache = solution.LRUCache(1)
        cache.put("x", 0)
        sentinel = object()
        self.assertIs(cache.get("missing", sentinel), sentinel)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("x"), 0)
    def test_none_and_falsey_hits_refresh(self):
        for value in [None, False, "", 0]:
            cache = solution.LRUCache(2)
            cache.put("a", value)
            cache.put("b", 2)
            self.assertEqual(cache.get("a", "fallback"), value)
            cache.put("c", 3)
            self.assertEqual(cache.get("b", "gone"), "gone")
    def test_capacity_one(self):
        cache = solution.LRUCache(1)
        cache.put(0, "first")
        cache.put(0, "updated")
        self.assertEqual(cache.get(0), "updated")
        cache.put(1, "second")
        self.assertIsNone(cache.get(0))
        self.assertEqual(len(cache), 1)
    def test_invalid_capacity(self):
        for value in [0, -1, True, 1.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.LRUCache(value)

if __name__ == "__main__":
    unittest.main()
