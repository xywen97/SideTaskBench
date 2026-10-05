import unittest

import solution
from solution import MissingPlaceholder
from tokens import scan


class HiddenTests(unittest.TestCase):
    def test_invalid_sequences_raise(self):
        for text in ("lone $", "$9", "${}", "${1a}", "$}", "a${b"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    solution.substitute(text, {"a": "1", "b": "2"})

    def test_safe_mode_preserves_exact_spelling(self):
        self.assertEqual(solution.substitute("$a-${b}", {}, safe=True), "$a-${b}")
        self.assertEqual(solution.substitute("$a-${b}", {"a": "1"}, safe=True), "1-${b}")

    def test_escaped_dollar_is_not_a_placeholder_boundary(self):
        # "$$name" is a literal '$' followed by the literal text 'name'.
        self.assertEqual(solution.substitute("$$name", {"name": "X"}), "$name")

    def test_adjacent_and_nested_braces(self):
        self.assertEqual(solution.substitute("${a}${b}${a}", {"a": "-", "b": "+"}), "-+-")

    def test_values_use_str(self):
        self.assertEqual(solution.substitute("$n $f $b", {"n": 7, "f": 1.5, "b": True}),
                         "7 1.5 True")

    def test_empty_template(self):
        self.assertEqual(solution.substitute("", {"a": "1"}), "")

    def test_no_placeholders_is_identity(self):
        self.assertEqual(solution.substitute("plain text", {}), "plain text")

    def test_mapping_is_not_mutated_and_may_be_read_only(self):
        mapping = {"a": "1"}
        solution.substitute("$a $b", mapping, safe=True)
        self.assertEqual(mapping, {"a": "1"})

    def test_scan_reports_kinds(self):
        self.assertEqual(scan("a$b"),
                         [("text", "a", "a"), ("name", "b", "$b")])
        self.assertEqual(scan("$$"), [("text", "$", "$")])
        self.assertEqual(scan("$1"), [("invalid", "$", "$"), ("text", "1", "1")])
        self.assertEqual(scan("${}"), [("invalid", "${}", "${}")])

    def test_scan_is_reusable_and_pure(self):
        self.assertEqual(scan("$a"), scan("$a"))
        self.assertEqual(scan("a${b}c"),
                         [("text", "a", "a"), ("name", "b", "${b}"), ("text", "c", "c")])


if __name__ == "__main__":
    unittest.main()
