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
    def test_interior_blank_lines_ignored(self):
        text = '{"id":1}\n\n{"id":2}\n   \n{"id":3}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"id": 1}, {"id": 2}, {"id": 3}],
        )

    def test_leading_and_trailing_blank_lines_ignored(self):
        text = "\n  \n{\"id\":1}\n\t\n"
        self.assertEqual(solution.load_jsonl(text), [{"id": 1}])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(solution.load_jsonl(""), [])
        self.assertEqual(solution.load_jsonl("\n \n\t\n"), [])

    def test_invalid_json_reports_physical_line_number(self):
        text = '{"id":1}\n\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_invalid_json_first_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl("nope")
        self.assertIn("line 1", str(ctx.exception))

    def test_non_object_raises_with_physical_line_number(self):
        # Valid JSON that is not an object must be rejected, not skipped.
        text = '{"id":1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_after_blank_line_number(self):
        text = '{"id":1}\n\n5'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_preserves_order_and_contents(self):
        text = '{"b":2,"a":1}\n{"z":[3,{"y":4}]}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2, "a": 1}, {"z": [3, {"y": 4}]}],
        )

    def test_does_not_skip_erroneous_nonblank_line(self):
        # A blank line is skipped, but the malformed line after it is not.
        text = '{"id":1}\n   \n{"id":2\n{"id":3}'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
