import unittest

import solution


class LineNumberRegressionTests(unittest.TestCase):
    def test_blank_lines_do_not_shift_numbers(self):
        # Blank lines (including leading) must still count as physical lines.
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('\n\n{"a": 1}\n{oops}\n')
        self.assertIn("line 4", str(ctx.exception))

    def test_invalid_json_first_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{not json}\n')
        self.assertIn("line 1", str(ctx.exception))

    def test_leading_whitespace_blank_is_ignored(self):
        self.assertEqual(
            solution.load_jsonl('   \n{"a": 1}\n\t\n'),
            [{"a": 1}],
        )

    def test_non_object_json_raises_with_line(self):
        for payload in ("[1, 2, 3]", '"hello"', "42", "true", "null"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl('{"ok": 1}\n' + payload + "\n")
            self.assertIn("line 2", str(ctx.exception))

    def test_contents_and_order_preserved(self):
        records = solution.load_jsonl('{"z": 1, "a": 2}\n{"m": 3}\n')
        self.assertEqual(list(records[0].keys()), ["z", "a"])
        self.assertEqual(records, [{"z": 1, "a": 2}, {"m": 3}])

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"emoji": "\\u00e9", "text": "\u2603"}\n'),
            [{"emoji": "\u00e9", "text": "\u2603"}],
        )

    def test_blank_only_variants(self):
        for payload in ("", " ", "\n", "\n\n", " \t \n \r\n"):
            self.assertEqual(solution.load_jsonl(payload), [])

    def test_trailing_newline_and_crlf(self):
        self.assertEqual(
            solution.load_jsonl(' \r\n{"x": 1}\r\n\r\n'),
            [{"x": 1}],
        )

    def test_error_does_not_skip_to_later_lines(self):
        # The very first bad nonblank line must raise; later good lines
        # must not cause the error to be swallowed.
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"a": 1}\n{bad}\n{"c": 3}\n')


if __name__ == "__main__":
    unittest.main()
