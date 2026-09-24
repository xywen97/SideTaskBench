import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_leading_blank_lines_preserve_physical_numbers(self):
        # A malformed record on physical line 3 must be reported as line 3,
        # not line 1 (the old strip()-before-numbering bug).
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("\n\n{bad}\n")
        self.assertIn("line 3", str(ctx.exception))

    def test_trailing_blank_lines_ignored(self):
        self.assertEqual(
            solution.load_jsonl('{"id":1}\n\n   \n\t\n'),
            [{"id": 1}],
        )

    def test_non_object_value_reports_line_number(self):
        for value in ("[1, 2]", '"text"', "42", "true", "null"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl('{"ok": 1}\n%s\n' % value)
            self.assertIn("line 2", str(ctx.exception))

    def test_non_object_at_first_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("[1, 2, 3]\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_error_line_does_not_skip_earlier_records(self):
        # Whitespace-only lines interleaved; the bad line is still located
        # by its physical position.
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"a": 1}\n  \nnot json\n{"b": 2}\n')
        self.assertIn("line 3", str(ctx.exception))

    def test_order_and_contents_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"b": 1}\n{"a": 2}\n{"b": 3}\n'),
            [{"b": 1}, {"a": 2}, {"b": 3}],
        )

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"name": "\u00e9\u4e2d\u6587"}\n'),
            [{"name": "\u00e9\u4e2d\u6587"}],
        )

    def test_empty_and_blank_only_inputs(self):
        self.assertEqual(solution.load_jsonl(""), [])
        self.assertEqual(solution.load_jsonl("\n\n"), [])
        self.assertEqual(solution.load_jsonl("   \t  "), [])

    def test_crlf_line_endings(self):
        self.assertEqual(
            solution.load_jsonl('{"id":1}\r\n\r\n{"id":2}\r\n'),
            [{"id": 1}, {"id": 2}],
        )

    def test_valueerror_type_is_raised(self):
        with self.assertRaises(ValueError):
            solution.load_jsonl("nope\n")


if __name__ == "__main__":
    unittest.main()
