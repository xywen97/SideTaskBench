import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_invalid_physical_line(self):
        with self.assertRaisesRegex(ValueError, r"line 4\b"):
            solution.load_jsonl('\n{"ok":true}\n \nnot-json\n')
    def test_non_object(self):
        for value in ['[]', '3', 'null', '"hello"', 'true']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, r"line 2\b"):
                solution.load_jsonl('\n' + value)
    def test_nested_and_crlf(self):
        self.assertEqual(solution.load_jsonl('\r\n{"x":[1,null],"t":"λ"}\r\n\t\r\n{}'), [{"x": [1, None], "t": "λ"}, {}])
    def test_error_is_not_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, r"line 2\b"):
            solution.load_jsonl('{"a":1}\n{broken}\n{"a":2}')
    def test_whitespace_around_object(self):
        self.assertEqual(solution.load_jsonl('  {"n": 0} \n \t {}  '), [{"n": 0}, {}])
    def test_unicode_line_separator_inside_string(self):
        self.assertEqual(solution.load_jsonl('{"text":"a\u2028b"}\n'), [{"text": "a\u2028b"}])

if __name__ == "__main__":
    unittest.main()
