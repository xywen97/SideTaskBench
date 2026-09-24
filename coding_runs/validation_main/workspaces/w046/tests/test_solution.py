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
    def test_header_only_returns_empty(self):
        self.assertEqual(solution.read_records("name,note\n"), [])
        self.assertEqual(solution.read_records("name,note"), [])

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_lf_mixed_with_crlf_records(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\ntwo"\r\nBob,"three\r\nfour"\r\n'),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "three\r\nfour"},
            ],
        )

    def test_escaped_quotes_commas_and_blank_fields(self):
        text = 'a,b,c\n"x,""y",,z\n'
        self.assertEqual(
            solution.read_records(text),
            [{"a": 'x,"y', "b": "", "c": "z"}],
        )

    def test_multiple_records_with_blank_quoted_field(self):
        text = 'name,note\nAda,"line1\nline2"\nBob,\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"name": "Ada", "note": "line1\nline2"},
                {"name": "Bob", "note": ""},
            ],
        )


if __name__ == "__main__":
    unittest.main()
