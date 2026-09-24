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

    def test_blank_fields(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_embedded_comma_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one, two"\n'),
            [{"name": "Ada", "note": "one, two"}],
        )

    def test_embedded_crlf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\nBob,hi\r\n"),
            [{"name": "Ada", "note": "hello"}, {"name": "Bob", "note": "hi"}],
        )

    def test_multiple_records_with_embedded_newlines(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nBob,three\n'),
            [{"name": "Ada", "note": "one\ntwo"}, {"name": "Bob", "note": "three"}],
        )


if __name__ == "__main__":
    unittest.main()
