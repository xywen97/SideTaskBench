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

    def test_preserve_crlf_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_preserve_lf_inside_quoted_field_crlf_records(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\ntwo"}],
        )

    def test_commas_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b,c"\n'),
            [{"name": "Ada", "note": "a,b,c"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"she said ""hi"""\n'),
            [{"name": "Ada", "note": 'she said "hi"'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n,b\n"),
            [{"name": "Ada", "note": ""}, {"name": "", "note": "b"}],
        )

    def test_multiple_records_with_multiline_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nBob,three\n'),
            [{"name": "Ada", "note": "one\ntwo"}, {"name": "Bob", "note": "three"}],
        )


if __name__ == "__main__":
    unittest.main()
