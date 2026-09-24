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

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_lf_keeps_both_newlines(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"line1\nline2\nline3"\n'),
            [{"name": "Ada", "note": "line1\nline2\nline3"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_field_and_comma_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('a,b,c\n"x,y","",z\n'),
            [{"a": "x,y", "b": "", "c": "z"}],
        )

    def test_multiple_records_with_multiline_field(self):
        self.assertEqual(
            solution.read_records('id,note\n1,"a\nb"\n2,plain\n'),
            [{"id": "1", "note": "a\nb"}, {"id": "2", "note": "plain"}],
        )


if __name__ == "__main__":
    unittest.main()
