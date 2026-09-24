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

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"id":1}'), [{"id": 1}])

    def test_blank_lines_at_both_ends(self):
        self.assertEqual(
            solution.load_jsonl('\n\n{"id":1}\n{"id":2}\n\n\n'),
            [{"id": 1}, {"id": 2}],
        )

    def test_preserves_order_and_contents(self):
        text = '{"b":2}\n{"a":1}\n{"nested":{"x":[1,2,3]}}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2}, {"a": 1}, {"nested": {"x": [1, 2, 3]}}],
        )

    def test_invalid_json_reports_physical_line(self):
        text = '{"id":1}\n\nnot json\n{"id":2}'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_leading_blank_lines_shift_numbering(self):
        text = '\n\n{"id":1}\n{broken}'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_non_object_json_reports_line(self):
        for payload in ("42", '"str"', "[1, 2]", "null", "true"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(payload)
            self.assertIn("line 1", str(ctx.exception))

    def test_non_object_after_valid_object_reports_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"id":1}\n[1, 2]')
        self.assertIn("line 2", str(ctx.exception))

    def test_does_not_skip_erroneous_nonblank_line(self):
        # A malformed nonblank record must raise rather than being ignored.
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"ok":true}\n   \n{DEFINITELY NOT JSON}\n{"ok":false}')

    def test_crlf_line_endings(self):
        self.assertEqual(
            solution.load_jsonl('{"id":1}\r\n{"id":2}\r\n'),
            [{"id": 1}, {"id": 2}],
        )

    def test_unusual_whitespace_lines_ignored(self):
        self.assertEqual(
            solution.load_jsonl('\t\n{"id":1}\n \t \n{"id":2}\n\t'),
            [{"id": 1}, {"id": 2}],
        )


if __name__ == "__main__":
    unittest.main()
