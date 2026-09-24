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

    def test_header_only_no_trailing_newline(self):
        self.assertEqual(solution.read_records("name,note"), [])

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_multiple_records_with_embedded_newline(self):
        text = 'name,note\nAda,"one\ntwo"\nGrace,"three\nfour"\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Grace", "note": "three\nfour"},
            ],
        )

    def test_embedded_comma_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one,two"\n'),
            [{"name": "Ada", "note": "one,two"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n"),
            [{"name": "Ada", "note": ""}],
        )

    def test_blank_quoted_field_value(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,""\n'),
            [{"name": "Ada", "note": ""}],
        )


if __name__ == "__main__":
    unittest.main()
