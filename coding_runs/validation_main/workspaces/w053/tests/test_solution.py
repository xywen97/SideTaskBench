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
        text = "\n\n  \n{\"a\":1}\n\t\n{\"b\":2}\n\n "
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_invalid_json_reports_physical_line(self):
        text = "{\"id\":1}\n\n{bad}\n{\"id\":3}\n"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("{oops}\n{\"id\":2}\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_non_object_value_reports_physical_line(self):
        text = '{"id":1}\n\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_scalar(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('42')
        self.assertIn("line 1", str(ctx.exception))

    def test_blank_lines_do_not_hide_previous_error(self):
        # A malformed nonblank line must never be treated as blank.
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('   \nnot json\n')
        self.assertIn("line 2", str(ctx.exception))

    def test_preserves_order_and_contents(self):
        text = '{"z": 1, "a": 2}\n{"m": [3, 4], "n": {"x": 5}}\n'
        result = solution.load_jsonl(text)
        self.assertEqual(
            result,
            [{"z": 1, "a": 2}, {"m": [3, 4], "n": {"x": 5}}],
        )
        # Object key order is preserved.
        self.assertEqual(list(result[0].keys()), ["z", "a"])
        self.assertEqual(list(result[1].keys()), ["m", "n"])

    def test_unicode_preserved(self):
        self.assertEqual(solution.load_jsonl('{"s": "\\u00e9\\u4e2d"}'), [{"s": "\u00e9\u4e2d"}])

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"id":1}'), [{"id": 1}])


if __name__ == "__main__":
    unittest.main()
