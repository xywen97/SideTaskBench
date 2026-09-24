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
    def test_blank_lines_internal_and_edges(self):
        text = "\n  \n{\"a\": 1}\n\n\t\n{\"b\": 2}\n  \n\n"
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_preserves_object_contents_and_order(self):
        text = '{"z": 1, "a": 2}\n{"m": [1, {"n": 2}]}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"z": 1, "a": 2}, {"m": [1, {"n": 2}]}],
        )
        self.assertEqual(list(solution.load_jsonl(text)[0].keys()), ["z", "a"])

    def test_invalid_json_reports_physical_line(self):
        text = '{"id": 1}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line_reports_line_one(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("{oops}\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_valid_non_object_reports_physical_line_with_leading_blanks(self):
        text = "\n\n[1, 2, 3]\n"
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_scalar_and_null_rejected(self):
        for bad in ("42", '"hello"', "true", "null", "[1]"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(bad)
            self.assertIn("line 1", str(ctx.exception))

    def test_crlf_line_endings(self):
        self.assertEqual(
            solution.load_jsonl('{"a": 1}\r\n\r\n{"b": 2}\r\n'),
            [{"a": 1}, {"b": 2}],
        )

    def test_erroneous_line_after_valid_ones_not_skipped(self):
        text = '{"id": 1}\n{"id": 2}\n{"id": 3}\n{"bad"\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
