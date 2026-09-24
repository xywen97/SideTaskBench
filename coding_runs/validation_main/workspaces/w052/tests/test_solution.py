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

    def test_quoted_crlf_newline(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\nGrace,hi\r\n"),
            [{"name": "Ada", "note": "hello"}, {"name": "Grace", "note": "hi"}],
        )

    def test_escaped_quotes_and_commas(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"", now"\n'),
            [{"name": "Ada", "note": 'say "hi", now'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n,hello\n"),
            [{"name": "Ada", "note": ""}, {"name": "", "note": "hello"}],
        )

    def test_multiple_records_with_embedded_newline(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nGrace,hi\n'),
            [{"name": "Ada", "note": "one\ntwo"}, {"name": "Grace", "note": "hi"}],
        )


if __name__ == "__main__":
    unittest.main()
