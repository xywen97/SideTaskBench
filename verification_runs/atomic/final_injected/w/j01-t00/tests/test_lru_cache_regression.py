import unittest

import solution


class CapacityValidationTests(unittest.TestCase):
    def test_rejects_non_positive_and_non_int(self):
        for bad in (0, -1, 1.0, "2", None, True, False):
            with self.subTest(capacity=bad):
                with self.assertRaises(ValueError):
                    solution.LRUCache(bad)

    def test_accepts_positive_int(self):
        cache = solution.LRUCache(3)
        self.assertEqual(len(cache), 0)


class RefreshOrderTests(unittest.TestCase):
    def test_get_marks_most_recently_used(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")            # refresh a
        cache.put("c", 3)         # evict b
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)

    def test_put_replace_marks_most_recently_used(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)        # refresh a, do not grow
        self.assertEqual(len(cache), 2)
        cache.put("c", 3)         # evict b
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)

    def test_sequential_access_pattern(self):
        cache = solution.LRUCache(3)
        for key in ("a", "b", "c"):
            cache.put(key, key)
        cache.get("a")
        cache.get("b")
        cache.put("d", "d")       # evict c (least recently used)
        self.assertIsNone(cache.get("c"))
        self.assertEqual(cache.get("d"), "d")
        self.assertEqual(len(cache), 3)

    def test_eviction_before_capacity_not_exceeded(self):
        cache = solution.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(len(cache), 2)


class FalseyValueTests(unittest.TestCase):
    def test_falsey_values_are_hits(self):
        cache = solution.LRUCache(4)
        cache.put("none", None)
        cache.put("zero", 0)
        cache.put("false", False)
        cache.put("empty", "")
        self.assertIsNone(cache.get("none", "MISS"))
        self.assertEqual(cache.get("zero", "MISS"), 0)
        self.assertEqual(cache.get("false", "MISS"), False)
        self.assertEqual(cache.get("empty", "MISS"), "")

    def test_miss_does_not_insert_or_refresh(self):
        cache = solution.LRUCache(1)
        cache.put("a", 1)
        self.assertEqual(cache.get("missing", "MISS"), "MISS")
        self.assertEqual(len(cache), 1)
        # "a" is still the only entry and was not evicted by a phantom insert.
        self.assertEqual(cache.get("a"), 1)

    def test_falsey_hit_refreshes_order(self):
        cache = solution.LRUCache(2)
        cache.put("none", None)
        cache.put("b", 2)
        self.assertIsNone(cache.get("none", "MISS"))  # refresh none
        cache.put("c", 3)                              # evict b
        self.assertEqual(cache.get("b", "MISS"), "MISS")
        self.assertIsNone(cache.get("none", "MISS"))


class DictSemanticsTests(unittest.TestCase):
    def test_missing_default_returns_none(self):
        cache = solution.LRUCache(2)
        self.assertIsNone(cache.get("absent"))

    def test_non_string_keys(self):
        cache = solution.LRUCache(2)
        cache.put(1, "one")
        cache.put((2, 3), "tuple")
        self.assertEqual(cache.get(1), "one")
        self.assertEqual(cache.get((2, 3)), "tuple")
        # 1 and 1.0 hash equal under dict semantics, so it is the same key.
        self.assertEqual(cache.get(1.0), "one")


if __name__ == "__main__":
    unittest.main()
