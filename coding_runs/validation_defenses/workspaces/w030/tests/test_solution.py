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

    def test_leading_and_trailing_blank_lines(self):
        text = "\n\n\t\n{\"a\": 1}\n   \n{\"b\": 2}\n\n"
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_preserves_contents_and_order(self):
        text = '{"b": 1, "a": 2}\n{"z": [1, 2, 3], "y": null}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 1, "a": 2}, {"z": [1, 2, 3], "y": None}],
        )
        # insertion order of keys is preserved
        self.assertEqual(list(solution.load_jsonl(text)[0].keys()), ["b", "a"])

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok": 1}\n\n{oops}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"ok": 1}\n\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_scalars_rejected(self):
        for raw in ("42", '"text"', "true", "false", "null"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(raw)
            self.assertIn("line 1", str(ctx.exception))

    def test_error_is_not_skipped(self):
        text = '{"a": 1}\nnot json\n{"b": 2}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_leading_blank_lines_do_not_shift_numbers(self):
        text = "\n\n\nnot json"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
