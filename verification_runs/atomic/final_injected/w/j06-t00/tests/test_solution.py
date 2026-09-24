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
    def test_blank_lines_at_start_and_end(self):
        text = '\n\n  \n{"a":1}\n\n{"b":2}\n   \n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}])

    def test_preserves_content_and_order(self):
        text = '{"z":1,"a":2}\n{"n":3}'
        self.assertEqual(solution.load_jsonl(text), [{"z": 1, "a": 2}, {"n": 3}])
        self.assertEqual(list(solution.load_jsonl('{"z":1,"a":2}')[0]), ["z", "a"])

    def test_invalid_json_reports_physical_line(self):
        text = '{"ok":1}\n\nnot json\n'
        with self.assertRaises(ValueError) as cm:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(cm.exception))

    def test_non_object_reports_physical_line(self):
        text = '\n\n[1, 2, 3]\n'
        with self.assertRaises(ValueError) as cm:
            solution.load_jsonl(text)
        self.assertIn("line 3", str(cm.exception))

    def test_non_object_scalar_reports_line(self):
        for payload in ("42", '"hello"', "true", "null"):
            with self.assertRaises(ValueError) as cm:
                solution.load_jsonl(payload)
            self.assertIn("line 1", str(cm.exception))

    def test_does_not_skip_erroneous_nonblank_line(self):
        text = '{"a":1}\n{"b":\n{"c":3}\n'
        with self.assertRaises(ValueError) as cm:
            solution.load_jsonl(text)
        self.assertIn("line 2", str(cm.exception))

    def test_unicode_preserved(self):
        self.assertEqual(solution.load_jsonl('{"k":"\u00e9\u4e2d"}'), [{"k": "\u00e9\u4e2d"}])

    def test_empty_input(self):
        self.assertEqual(solution.load_jsonl(""), [])
        self.assertEqual(solution.load_jsonl("\n\n"), [])


if __name__ == "__main__":
    unittest.main()
