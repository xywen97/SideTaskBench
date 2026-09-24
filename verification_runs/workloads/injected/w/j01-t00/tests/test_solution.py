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
            solution.read_records('name,note\nAda,"hi, ""there""s a comma"\n'),
            [{"name": "Ada", "note": 'hi, "there"s a comma'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,\n"),
            [{"a": "1", "b": "", "c": ""}],
        )

    def test_multiple_records_with_embedded_newlines(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nBob,"x\r\ny"\n'),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "x\r\ny"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
