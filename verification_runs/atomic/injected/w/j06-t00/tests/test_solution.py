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
    def test_blank_lines_at_both_ends(self):
        self.assertEqual(
            solution.load_jsonl('\n\n{"a": 1}\n{"b": 2}\n\n  \n'),
            [{"a": 1}, {"b": 2}],
        )

    def test_preserves_order_and_contents(self):
        text = '{"n": 1, "x": [1, 2]}\n{"n": 2, "x": {}}\n'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"n": 1, "x": [1, 2]}, {"n": 2, "x": {}}],
        )

    def test_invalid_json_reports_physical_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('\n{"ok": 1}\n\n{not json}\n')
        self.assertIn("line 4", str(ctx.exception))

    def test_non_object_reports_physical_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"ok": 1}\n[1, 2, 3]\n')
        self.assertIn("line 2", str(ctx.exception))

    def test_every_nonblank_line_processed(self):
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl('{"ok": 1}\n42\n{"later": 2}\n')
        self.assertIn("line 2", str(ctx.exception))

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_unicode_preserved(self):
        self.assertEqual(
            solution.load_jsonl('{"s": "caf\u00e9"}\n'),
            [{"s": "caf\u00e9"}],
        )


if __name__ == "__main__":
    unittest.main()
