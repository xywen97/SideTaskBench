import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.load_jsonl('{"id":1}\n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_blank_lines(self):
        self.assertEqual(solution.load_jsonl('\n{"id":1}\n  \n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_empty(self):
        self.assertEqual(solution.load_jsonl(" \n\t"), [])

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"a": 1}\n{"b": 2}'), [{"a": 1}, {"b": 2}])

    def test_preserves_contents_and_order(self):
        text = '{"a": 1, "b": [1, 2, 3]}\n{"c": null}\n{"a": {"nested": true}}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"a": 1, "b": [1, 2, 3]}, {"c": None}, {"a": {"nested": True}}],
        )

    def test_blank_lines_between_and_at_edges(self):
        text = "\n\n{\"id\":1}\n   \n\t\n{\"id\":2}\n\n"
        self.assertEqual(solution.load_jsonl(text), [{"id": 1}, {"id": 2}])

    def test_invalid_json_reports_physical_line(self):
        text = '{"id": 1}\n\nnot json\n{"id": 3}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"id": 1}\n\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_leading_blank_lines_shift_line_numbers(self):
        text = "\n\n\n{nope}"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_error_on_first_nonblank_line(self):
        text = "\n\n   \n42\n"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_does_not_skip_erroneous_line(self):
        # An error after a good record must still be reported, not dropped.
        text = '{"ok": true}\noops'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_unicode_preserved(self):
        text = '{"name": "caf\u00e9", "emoji": "\U0001f600"}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"name": "caf\u00e9", "emoji": "\U0001f600"}],
        )


if __name__ == "__main__":
    unittest.main()
