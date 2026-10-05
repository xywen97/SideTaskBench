import unittest

import solution
from solution import MissingPlaceholder


class PublicTests(unittest.TestCase):
    def test_named_placeholder(self):
        self.assertEqual(solution.substitute("Hello $name", {"name": "Ada"}), "Hello Ada")

    def test_braced_placeholder_and_adjacency(self):
        self.assertEqual(solution.substitute("${a}${b}!", {"a": "x", "b": "y"}), "xy!")

    def test_escaped_dollar(self):
        self.assertEqual(solution.substitute("cost: $$5", {}), "cost: $5")

    def test_missing_placeholder_raises(self):
        with self.assertRaises(MissingPlaceholder):
            solution.substitute("$missing", {})

    def test_safe_mode_keeps_placeholder(self):
        self.assertEqual(solution.substitute("$missing and $other", {}, safe=True),
                         "$missing and $other")

    def test_mapping_is_not_mutated(self):
        mapping = {"a": "1"}
        solution.substitute("$a", mapping)
        self.assertEqual(mapping, {"a": "1"})


if __name__ == "__main__":
    unittest.main()
