import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.read_records("name,note\nAda,hello\n"), [{"name": "Ada", "note": "hello"}])
    def test_quoted_newline(self):
        self.assertEqual(solution.read_records('name,note\nAda,"one\ntwo"\n'), [{"name": "Ada", "note": "one\ntwo"}])
    def test_empty(self):
        self.assertEqual(solution.read_records(""), [])


class RegressionTests(unittest.TestCase):
    def test_header_only(self):
        self.assertEqual(solution.read_records("name,note\n"), [])
        self.assertEqual(solution.read_records("name,note"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_quoted_crlf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_commas_blank_fields_and_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('a,b,c\n"x,y",,"he said ""hi"""\n'),
            [{"a": "x,y", "b": "", "c": 'he said "hi"'}],
        )

    def test_multiple_multiline_records(self):
        text = 'a,b\n"l1\nl2","q""r\ns"\nplain,tail\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"a": "l1\nl2", "b": 'q"r\ns'},
                {"a": "plain", "b": "tail"},
            ],
        )

    def test_no_trailing_newline(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,hello"),
            [{"name": "Ada", "note": "hello"}],
        )


if __name__ == "__main__":
    unittest.main()
