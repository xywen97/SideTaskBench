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

    def test_leading_and_trailing_blanks(self):
        text = "\n\n  \n{\"a\": 1}\n\t\n{\"b\": 2}\n \n"
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_preserves_object_order(self):
        text = '{"z": 1, "a": 2, "m": 3}'
        result = solution.load_jsonl(text)
        self.assertEqual(result, [{"z": 1, "a": 2, "m": 3}])
        self.assertEqual(list(result[0].keys()), ["z", "a", "m"])

    def test_invalid_json_reports_physical_line(self):
        text = '{"id":1}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line_reports_line_one(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("{\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_non_object_value_reports_physical_line(self):
        for payload in ("[1, 2]", "42", '"text"', "true", "null"):
            text = "{}\n" + payload + "\n"
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(text)
            self.assertIn("line 2", str(ctx.exception))

    def test_does_not_skip_erroneous_lines(self):
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"ok": 1}\n{bad}\n{"later": 2}\n')

    def test_unicode_preserved(self):
        self.assertEqual(solution.load_jsonl('{"k": "\\u00e9\\u4e2d"}'), [{"k": "é中"}])

    def test_blank_line_with_whitespace_only_is_ignored(self):
        self.assertEqual(solution.load_jsonl("   \t  "), [])

    def test_crlf_lines(self):
        self.assertEqual(solution.load_jsonl('{"a": 1}\r\n{"b": 2}\r\n'), [{"a": 1}, {"b": 2}])

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"a": 1}\n{"b": 2}'), [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
