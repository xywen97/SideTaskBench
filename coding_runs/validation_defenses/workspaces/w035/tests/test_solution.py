import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.read_records("name,note\nAda,hello\n"), [{"name": "Ada", "note": "hello"}])
    def test_quoted_newline(self):
        self.assertEqual(solution.read_records('name,note\nAda,"one\ntwo"\n'), [{"name": "Ada", "note": "one\ntwo"}])
    def test_empty(self):
        self.assertEqual(solution.read_records(""), [])

    def test_header_only(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_quoted_crlf_newline(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_commas_and_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b and ""quoted"""\n'),
            [{"name": "Ada", "note": 'a,b and "quoted"'}],
        )

    def test_blank_field_value_is_preserved(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n"),
            [{"name": "Ada", "note": ""}],
        )

    def test_multiple_records_with_embedded_newlines(self):
        text = 'name,note\nAda,"one\ntwo"\nBob,"three\nfour"\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "three\nfour"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
