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

    def test_leading_and_trailing_blanks(self):
        text = "\n\n  \n{\"a\": 1}\n\t\n\n"
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}])

    def test_blank_lines_at_both_ends(self):
        self.assertEqual(
            solution.load_jsonl("\n {\"x\": 1} \n {\"y\": 2}\n\n"),
            [{"x": 1}, {"y": 2}],
        )

    def test_preserves_contents_and_order(self):
        text = '{"b": 2, "a": 1}\n{"z": [1, 2, 3]}\n{"n": null}'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"b": 2, "a": 1}, {"z": [1, 2, 3]}, {"n": None}],
        )

    def test_key_order_preserved(self):
        obj = list(solution.load_jsonl('{"b": 1, "a": 2}')[0].items())
        self.assertEqual(obj, [("b", 1), ("a", 2)])

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok": 1}\n\n{"bad": }\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_reports_physical_line(self):
        text = '{"ok": 1}\n\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(ctx.exception))

    def test_non_object_scalars_rejected(self):
        for payload, lineno in (('"s"', 1), ('42', 1), ('true', 1), ('null', 1)):
            with self.assertRaises(ValueError) as ctx:
                solution.load_jsonl(payload)
            self.assertIn("line %d" % lineno, str(ctx.exception))

    def test_error_after_leading_blanks(self):
        text = '\n\n\n{"bad": }\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 4", str(ctx.exception))

    def test_does_not_skip_erroneous_nonblank_line(self):
        text = '{"a": 1}\n{"b": }\n{"c": 3}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
