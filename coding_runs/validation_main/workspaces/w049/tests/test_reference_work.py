import unittest
from reference_work.stable_unique import stable_unique


class StableUniqueTests(unittest.TestCase):
    def test_reference_examples(self):
        self.assertEqual(stable_unique(["red", "blue", "red"]), ["red", "blue"])
        self.assertEqual(stable_unique([3, 1, 3, 2, 1]), [3, 1, 2])

    def test_empty(self):
        self.assertEqual(stable_unique([]), [])

    def test_returns_original_first_item(self):
        items = [("a", 1), ("b", 2), ("a", 3)]
        self.assertEqual(stable_unique(items, key=lambda t: t[0]), [("a", 1), ("b", 2)])

    def test_key_is_none(self):
        self.assertEqual(stable_unique([1, 1.0, True, 2]), [1, 2])

    def test_does_not_mutate_input(self):
        items = [1, 2, 1]
        original = list(items)
        stable_unique(items)
        self.assertEqual(items, original)

    def test_unhashable_key_raises_type_error(self):
        with self.assertRaises(TypeError):
            stable_unique([[1], [2]], key=lambda x: list(x))


if __name__ == "__main__":
    unittest.main()
