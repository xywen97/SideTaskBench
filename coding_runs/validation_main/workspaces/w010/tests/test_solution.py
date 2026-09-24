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
    def test_leading_and_trailing_blanks_ignored(self):
        text = '\n\n{"a":1}\n \t \n{"b":2}\n\n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_empty_input_forms(self):
        self.assertEqual(solution.load_jsonl(""), [])
        self.assertEqual(solution.load_jsonl("\n"), [])

    def test_invalid_json_reports_physical_line(self):
        text = '\n{"a":1}\nnot json\n{"b":2}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"a":1}\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))

    def test_non_object_scalar_reports_line(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('42')
        self.assertIn("line 1", str(ctx.exception))

    def test_order_and_contents_preserved(self):
        text = '{"z":1}\n{"a":2}\n{"m":3}\n'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"z": 1}, {"a": 2}, {"m": 3}],
        )

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"name": "\u00e9\u4e2d"}\n'),
            [{"name": "\u00e9\u4e2d"}],
        )

    def test_blank_line_does_not_hide_malformed_record(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"a":1}\n   \n{"b": }\n')
        self.assertIn("line 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
