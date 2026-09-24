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
    def test_truly_empty_input(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_blank_lines_are_ignored_at_both_ends(self):
        text = '\n\n {"a": 1} \n\t\n{"b": 2}\n\n  \n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_physical_line_number_for_invalid_json(self):
        text = '\n{"ok": 1}\nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_physical_line_number_accounts_for_leading_blanks(self):
        text = '\n\n\n   \n{"bad": }\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 5", str(ctx.exception))

    def test_non_object_json_raises_with_line_number(self):
        for payload in ("42", '"text"', "[1, 2]", "true", "null"):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl('{"ok": 1}\n' + payload + "\n")
            self.assertIn("line 2", str(ctx.exception))

    def test_does_not_skip_erroneous_nonblank_line(self):
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"a": 1}\n{"b": 2}\ngarbage\n{"c": 3}\n')

    def test_order_and_contents_preserved(self):
        text = '{"z": 1, "a": 2}\n{"nested": {"x": [1, 2, 3]}, "u": "\u00e9"}'
        result = solution.load_jsonl(text)
        self.assertEqual(result[0], {"z": 1, "a": 2})
        self.assertEqual(list(result[0].keys()), ["z", "a"])
        self.assertEqual(result[1], {"nested": {"x": [1, 2, 3]}, "u": "\u00e9"})

    def test_no_trailing_newline(self):
        self.assertEqual(solution.load_jsonl('{"id":1}'), [{"id": 1}])


if __name__ == "__main__":
    unittest.main()
