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
        text = 'name,note\nAda,"a,b ""quoted"" c"\n'
        self.assertEqual(
            solution.read_records(text),
            [{"name": "Ada", "note": 'a,b "quoted" c'}],
        )

    def test_blank_fields(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n"),
            [{"name": "Ada", "note": ""}],
        )

    def test_multiple_records_and_multiline_field(self):
        text = 'name,note\nAda,"one\ntwo"\nBob,plain\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "plain"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
