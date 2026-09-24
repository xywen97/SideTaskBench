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
    def test_header_only_lf(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_header_only_crlf(self):
        self.assertEqual(solution.read_records("name,note\r\n"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        text = 'name,note\r\nAda,"one\r\ntwo"\r\n'
        self.assertEqual(
            solution.read_records(text),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_lf_in_crlf_stream(self):
        text = 'name,note\r\nAda,"one\ntwo"\r\n'
        self.assertEqual(
            solution.read_records(text),
            [{"name": "Ada", "note": "one\ntwo"}],
        )

    def test_escaped_double_quotes(self):
        text = 'name,note\nAda,"say ""hi"""\n'
        self.assertEqual(
            solution.read_records(text),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_comma_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b,c"\n'),
            [{"name": "Ada", "note": "a,b,c"}],
        )

    def test_multiple_records_with_embedded_newlines(self):
        text = 'name,note\nAda,"one\ntwo"\nBob,"three"\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "three"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
