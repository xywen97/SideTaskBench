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
        self.assertEqual(solution.load_jsonl('{"id":1}\n{"id":2}'), [{"id": 1}, {"id": 2}])

    def test_blank_lines_at_both_ends(self):
        text = '\n\n{"a":1}\n\n{"b":2}\n  \n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok":1}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_leading_blanks_preserve_physical_line_number(self):
        text = '\n\n\n{"bad":\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_non_object_json_reports_line(self):
        text = '{"a":1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_scalar_reports_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('42')
        self.assertIn("line 1", str(ctx.exception))

    def test_does_not_skip_erroneous_lines(self):
        # An error on a later nonblank line must not be silently dropped.
        text = '{"a":1}\n\n{"b":2}\ntrue\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_preserves_object_contents_and_order(self):
        text = '{"z":1,"a":2,"m":3}'
        parsed = solution.load_jsonl(text)
        self.assertEqual(parsed, [{"z": 1, "a": 2, "m": 3}])
        self.assertEqual(list(parsed[0].keys()), ["z", "a", "m"])

    def test_unicode_preserved(self):
        self.assertEqual(solution.load_jsonl('{"name":"caf\\u00e9"}'), [{"name": "caf\u00e9"}])

    def test_jsondecodeerror_is_valueerror(self):
        import json
        self.assertTrue(issubclass(json.JSONDecodeError, ValueError))


if __name__ == "__main__":
    unittest.main()
