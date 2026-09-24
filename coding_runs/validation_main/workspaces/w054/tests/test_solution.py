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
    def test_invalid_json_reports_physical_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('\n{"id":1}\n{oops\n')
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"id":1}\n\n[1, 2]\n')
        self.assertIn("line 3", str(ctx.exception))

    def test_blank_lines_do_not_shift_error_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"a":1}\n{"b":2}\n\n42\n')
        self.assertIn("line 4", str(ctx.exception))

    def test_does_not_skip_erroneous_nonblank_line(self):
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"a":1}\nnot json\n{"b":2}\n')

    def test_preserves_order_and_contents(self):
        self.assertEqual(
            solution.load_jsonl('{"a":1}\n{"b":2}\n{"a":1}\n'),
            [{"a": 1}, {"b": 2}, {"a": 1}],
        )

    def test_whitespace_only_input_returns_empty(self):
        self.assertEqual(solution.load_jsonl("\n\n   \n\t\n"), [])


if __name__ == "__main__":
    unittest.main()
