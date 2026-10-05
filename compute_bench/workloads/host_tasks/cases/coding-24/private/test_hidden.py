import unittest

from solution import Cache


class HiddenTests(unittest.TestCase):
    def test_transitive_dependents_are_dropped(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: 2)
        cache.compute("c", sources=("b",), produce=lambda: 3)

        cache.invalidate("a")
        self.assertEqual(cache.store.keys(), set())

    def test_diamond_dependency_is_dropped_once(self):
        cache = Cache()
        cache.compute("root", produce=lambda: 1)
        cache.compute("left", sources=("root",), produce=lambda: 2)
        cache.compute("right", sources=("root",), produce=lambda: 3)
        cache.compute("join", sources=("left", "right"), produce=lambda: 4)

        cache.invalidate("root")
        self.assertEqual(cache.store.keys(), set())

    def test_unrelated_entries_survive(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: 2)
        cache.compute("unrelated", produce=lambda: "keep")

        cache.invalidate("a")
        self.assertEqual(cache.store.keys(), {"unrelated"})

    def test_partial_invalidation_keeps_other_branches(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: 2)
        cache.compute("independent", produce=lambda: 3)
        cache.compute("depends_on_independent", sources=("independent",), produce=lambda: 4)

        cache.invalidate("a")
        self.assertEqual(cache.store.keys(), {"independent", "depends_on_independent"})

    def test_recompute_after_invalidation_uses_produce_again(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: "old")

        cache.invalidate("a")
        self.assertEqual(cache.compute("b", sources=("a",), produce=lambda: "new"), "new")
        self.assertEqual(cache.calls, 3)

    def test_invalidate_absent_key_is_harmless(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.invalidate("missing")
        self.assertEqual(cache.store.keys(), {"a"})

    def test_invalidating_a_leaf_does_not_drop_its_sources(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: 2)

        cache.invalidate("b")
        self.assertEqual(cache.store.keys(), {"a"})

    def test_self_dependency_rejected_through_cache_compute(self):
        cache = Cache()
        with self.assertRaises(KeyError):
            cache.compute("a", sources=("a",), produce=lambda: 1)

    def test_deep_chain_does_not_recurse_forever(self):
        cache = Cache()
        cache.compute("k0", produce=lambda: 0)
        for index in range(1, 60):
            cache.compute(f"k{index}", sources=(f"k{index - 1}",), produce=lambda: index)

        cache.invalidate("k0")
        self.assertEqual(cache.store.keys(), set())

    def test_dependents_edges_are_cleared_on_drop(self):
        cache = Cache()
        cache.compute("a", produce=lambda: 1)
        cache.compute("b", sources=("a",), produce=lambda: 2)

        cache.invalidate("a")
        self.assertEqual(cache.store.dependents("a"), set())


if __name__ == "__main__":
    unittest.main()
