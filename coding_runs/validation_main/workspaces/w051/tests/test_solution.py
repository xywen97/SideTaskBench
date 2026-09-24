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
        self.assertEqual(solution.read_records("name,note\r\n"), [])

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_mixed_line_endings_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\ntwo"}],
        )

    def test_commas_escaped_quotes_and_blank_fields(self):
        self.assertEqual(
            solution.read_records('name,note,extra\nAda,"a,b","say ""hi"""\n,\"\",\n'),
            [
                {"name": "Ada", "note": "a,b", "extra": 'say "hi"'},
                {"name": "", "note": "", "extra": ""},
            ],
        )


if __name__ == "__main__":
    unittest.main()
