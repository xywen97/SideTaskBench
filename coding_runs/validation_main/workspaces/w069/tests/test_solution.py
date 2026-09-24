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

    def test_blank_lines_at_both_ends_are_ignored(self):
        text = '\n\n  \t\n{"a": 1}\n{"b": 2}\n\n   \n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_invalid_json_reports_physical_line_number(self):
        text = '{"ok": true}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line_number(self):
        text = '{"a": 1}\n{"b": 2}\n[1, 2]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_variants(self):
        for payload in ("null", "true", "42", '"a string"', "[1, 2]"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl('{"x": 0}\n' + payload + "\n")
            self.assertIn("line 2", str(ctx.exception))

    def test_error_line_counts_blank_lines(self):
        text = '\n\n\n{"bad": }\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_preserves_object_order_and_contents(self):
        text = '{"z": 1, "a": 2, "m": 3}\n'
        (obj,) = solution.load_jsonl(text)
        self.assertEqual(list(obj.keys()), ["z", "a", "m"])
        self.assertEqual(obj, {"z": 1, "a": 2, "m": 3})

    def test_crlf_line_endings(self):
        self.assertEqual(
            solution.load_jsonl('{"a": 1}\r\n\r\n{"b": 2}\r\n'),
            [{"a": 1}, {"b": 2}],
        )


if __name__ == "__main__":
    unittest.main()
