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
        text = "\n\n  \n{\"id\":1}\n\t\n{\"id\":2}\n   \n\n"
        self.assertEqual(solution.load_jsonl(text), [{"id": 1}, {"id": 2}])

    def test_preserves_order_and_contents(self):
        text = '{"b":2,"a":1}\n{"a":3,"b":4}'
        records = solution.load_jsonl(text)
        self.assertEqual(records, [{"b": 2, "a": 1}, {"a": 3, "b": 4}])
        self.assertEqual(list(records[0].keys()), ["b", "a"])

    def test_invalid_json_reports_physical_line(self):
        text = '{"id":1}\n\n{not json}\n{"id":2}'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_with_leading_blank_line(self):
        text = "\n\n{bad}"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_number_reports_line(self):
        text = '{"id":1}\n42\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_array_reports_line(self):
        text = '{"id":1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_reports_first_offending_line(self):
        # The erroneous nonblank line must not be skipped.
        text = "null\n\"a string\"\n"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 1", str(ctx.exception))

    def test_crlf_line_endings(self):
        text = '{"id":1}\r\n\r\n{"id":2}\r\n'
        self.assertEqual(solution.load_jsonl(text), [{"id": 1}, {"id": 2}])

    def test_unicode_preserved(self):
        text = '{"name":"caf\u00e9 \u00fc"}'
        self.assertEqual(solution.load_jsonl(text), [{"name": "caf\u00e9 \u00fc"}])


if __name__ == "__main__":
    unittest.main()
