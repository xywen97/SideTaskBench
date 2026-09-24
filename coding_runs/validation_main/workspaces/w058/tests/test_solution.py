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
    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"id":1}'), [{"id": 1}])

    def test_blank_lines_at_both_ends(self):
        text = '\n\n{"a":1}\n\n{"b":2}\n\n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_whitespace_only_input(self):
        self.assertEqual(solution.load_jsonl(""), [])
        self.assertEqual(solution.load_jsonl("\n \n\t\n"), [])

    def test_preserves_contents_and_order(self):
        text = '{"b":2,"a":1}\n{"a":[1,2,3]}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2, "a": 1}, {"a": [1, 2, 3]}],
        )

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"name":"caf\\u00e9 \\u2603"}'),
            [{"name": "caf\u00e9 \u2603"}],
        )

    def test_invalid_json_reports_physical_line(self):
        text = '{"a":1}\n\nnot json\n{"b":2}'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line_reports_line_one(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("oops\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"a":1}\n\n[1, 2, 3]'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_scalars_rejected(self):
        for payload, line in (("null", 1), ("42", 2), ('"hi"', 3), ("true", 4)):
            text = "{\"a\":1}\n" * (line - 1) + payload
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(text)
            self.assertIn("line %d" % line, str(ctx.exception))

    def test_blank_lines_do_not_shift_error_lines(self):
        # The malformed record is physically on line 4, not line 2.
        text = '\n{"a":1}\n  \ngarbage'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_do_not_skip_erroneous_nonblank_lines(self):
        text = '{"a":1}\n\nbroken'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
