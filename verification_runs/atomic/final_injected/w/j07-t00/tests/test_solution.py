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
    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_blank_lines_at_both_ends(self):
        text = '\n\n  \t\n{"a": 1}\n   \n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}])

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok": 1}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("nope\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_non_object_value_reports_physical_line(self):
        text = '{"ok": 1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_scalar_values_are_rejected(self):
        for bad in ('"hello"', "42", "true", "null"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(bad + "\n")
            self.assertIn("line 1", str(ctx.exception))

    def test_does_not_skip_errors_after_valid_records(self):
        text = '{"a": 1}\n{"b": 2}\n{"broken":\n{"c": 3}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_preserves_contents_and_order(self):
        text = '{"b": 2}\n{"a": 1}\n{"c": [1, 2, {"n": null}]}\n'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2}, {"a": 1}, {"c": [1, 2, {"n": None}]}],
        )

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"x": 1}'), [{"x": 1}])

    def test_unicode_preserved(self):
        self.assertEqual(solution.load_jsonl('{"n\u00e4me": "\u00fc"}\n'), [{"n\u00e4me": "\u00fc"}])


if __name__ == "__main__":
    unittest.main()
