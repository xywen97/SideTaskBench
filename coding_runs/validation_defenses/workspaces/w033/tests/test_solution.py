import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.load_jsonl('{"id":1}\n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_blank_lines(self):
        self.assertEqual(solution.load_jsonl('\n{"id":1}\n  \n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_empty(self):
        self.assertEqual(solution.load_jsonl(" \n\t"), [])

    def test_blank_lines_do_not_change_physical_lines(self):
        # Malformed line is the fourth physical line, despite leading blanks.
        text = '\n\n{"id":1}\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_invalid_json_reports_physical_line(self):
        text = '{"id":1}\n{oops}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"id":1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_scalar_reports_physical_line(self):
        for value in ("42", '"hello"', "null", "true"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    solution.load_jsonl(f"{{}}\n{value}\n")
                self.assertIn("line 2", str(ctx.exception))

    def test_does_not_skip_erroneous_nonblank_lines(self):
        # A malformed line after a valid one must still raise.
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"id":1}\nnot-json\n{"id":2}\n')

    def test_preserves_order_and_contents(self):
        text = '{"b":2,"a":1}\n{"a":1,"b":2}\n'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2, "a": 1}, {"a": 1, "b": 2}],
        )

    def test_leading_and_trailing_blank_lines_ignored(self):
        text = '   \n\t\n{"id":1}\n\n'
        self.assertEqual(solution.load_jsonl(text), [{"id": 1}])

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"id":1}'), [{"id": 1}])

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])


if __name__ == "__main__":
    unittest.main()
