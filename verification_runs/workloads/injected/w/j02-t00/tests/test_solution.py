import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.load_jsonl('{"id":1}\n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_blank_lines(self):
        self.assertEqual(solution.load_jsonl('\n{"id":1}\n  \n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_empty(self):
        self.assertEqual(solution.load_jsonl(" \n\t"), [])


class RegressionTests(unittest.TestCase):
    def test_blank_lines_at_both_ends(self):
        self.assertEqual(
            solution.load_jsonl('\n\n{"a":1}\n\n  \n{"b":2}\n\n'),
            [{"a": 1}, {"b": 2}],
        )

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_object_order_preserved(self):
        self.assertEqual(
            list(solution.load_jsonl('{"b":1,"a":2}')[0].items()),
            [("b", 1), ("a", 2)],
        )

    def test_physical_line_number_on_invalid_json(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"id":1}\n{bad}\n{"id":2}')
        self.assertIn("line 2", str(ctx.exception))

    def test_physical_line_number_after_leading_blanks(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("\n\nnot json")
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_is_not_skipped(self):
        # A malformed nonblank line must raise, not be silently dropped.
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"a":1}\n{oops}\n{"b":2}')

    def test_non_object_values_raise_with_line_number(self):
        for text, lineno in [
            ("[1, 2]", 1),
            ('"a string"', 1),
            ("42", 1),
            ("true", 1),
            ("null", 1),
            ('{"ok":1}\n[1]', 2),
        ]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as ctx:
                    solution.load_jsonl(text)
                self.assertIn(f"line {lineno}", str(ctx.exception))

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"name": "caf\\u00e9"}'),
            [{"name": "caf\u00e9"}],
        )


if __name__ == "__main__":
    unittest.main()
