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
        text = "\n\n  \t\n{\"a\": 1}\n{\"b\": 2}\n\n   \n"
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_empty_string(self):
        self.assertEqual(solution.load_jsonl(""), [])

    def test_no_trailing_newline(self):
        self.assertEqual(
            solution.load_jsonl('{"a": 1}\n{"b": 2}'), [{"a": 1}, {"b": 2}]
        )

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok": 1}\n\nnot json\n'
        with self.assertRaises(ValueError) as cm:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(cm.exception))

    def test_non_object_values_rejected_with_line(self):
        cases = [
            ("[1, 2, 3]", "line 1"),
            ("42", "line 1"),
            ('"a string"', "line 1"),
            ("null", "line 1"),
            ("true", "line 1"),
            ('{"a": 1}\n[2]\n', "line 2"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as cm:
                    solution.load_jsonl(text)
                self.assertIn(expected, str(cm.exception))

    def test_erroneous_line_is_not_skipped(self):
        with self.assertRaises(ValueError):
            solution.load_jsonl('{"a": 1}\n{"b": 2} trailing\n{"c": 3}')

    def test_contents_and_order_preserved(self):
        text = '{"z": 1, "a": [1, 2], "n": null}\n{"k": "v"}\n'
        self.assertEqual(
            solution.load_jsonl(text),
            [{"z": 1, "a": [1, 2], "n": None}, {"k": "v"}],
        )

    def test_crlf_line_endings(self):
        self.assertEqual(
            solution.load_jsonl('{"a": 1}\r\n{"b": 2}\r\n'),
            [{"a": 1}, {"b": 2}],
        )


if __name__ == "__main__":
    unittest.main()
