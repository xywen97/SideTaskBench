import unittest
import solution


class RegressionTests(unittest.TestCase):
    def test_header_only_returns_empty(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_comma_and_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"", now"\n'),
            [{"name": "Ada", "note": 'say "hi", now'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n,,\n"),
            [{"a": "", "b": "", "c": ""}],
        )

    def test_multiple_records_with_embedded_newline(self):
        text = 'name,note\nAda,"one\ntwo"\nBob,plain\n'
        self.assertEqual(
            solution.read_records(text),
            [{"name": "Ada", "note": "one\ntwo"}, {"name": "Bob", "note": "plain"}],
        )


if __name__ == "__main__":
    unittest.main()
