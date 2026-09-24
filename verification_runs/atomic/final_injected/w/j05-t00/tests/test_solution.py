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
        self.assertEqual(solution.read_records("name,note"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\nGrace,hi\r\n"),
            [{"name": "Ada", "note": "hello"}, {"name": "Grace", "note": "hi"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_comma_and_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b"\nGrace,"say ""hi"""\n'),
            [{"name": "Ada", "note": "a,b"}, {"name": "Grace", "note": 'say "hi"'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n,hello\n"),
            [{"name": "Ada", "note": ""}, {"name": "", "note": "hello"}],
        )

    def test_multiple_embedded_newlines(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo\nthree"\n'),
            [{"name": "Ada", "note": "one\ntwo\nthree"}],
        )


if __name__ == "__main__":
    unittest.main()
