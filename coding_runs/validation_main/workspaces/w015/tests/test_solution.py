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
    def test_quoted_crlf_preserved(self):
        text = 'name,note\r\nAda,"one\r\ntwo"\r\n'
        self.assertEqual(solution.read_records(text), [{"name": "Ada", "note": "one\r\ntwo"}])

    def test_quoted_lf_preserved_with_crlf_records(self):
        text = 'name,note\r\nAda,"one\ntwo"\r\n'
        self.assertEqual(solution.read_records(text), [{"name": "Ada", "note": "one\ntwo"}])

    def test_escaped_double_quotes(self):
        text = 'name,note\nAda,"say ""hi"""\n'
        self.assertEqual(solution.read_records(text), [{"name": "Ada", "note": 'say "hi"'}])

    def test_comma_inside_quoted_field(self):
        text = 'a,b\n"x,y",z\n'
        self.assertEqual(solution.read_records(text), [{"a": "x,y", "b": "z"}])

    def test_blank_field_value(self):
        text = 'a,b\nx,\n'
        self.assertEqual(solution.read_records(text), [{"a": "x", "b": ""}])

    def test_header_only_lf(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_header_only_crlf(self):
        self.assertEqual(solution.read_records("name,note\r\n"), [])

    def test_no_trailing_newline(self):
        self.assertEqual(solution.read_records("name,note\nAda,hello"), [{"name": "Ada", "note": "hello"}])

    def test_multiple_records_with_embedded_newlines(self):
        text = 'id,note\r\n1,"a\r\nb"\r\n2,"c\nd"\r\n'
        self.assertEqual(
            solution.read_records(text),
            [{"id": "1", "note": "a\r\nb"}, {"id": "2", "note": "c\nd"}],
        )


if __name__ == "__main__":
    unittest.main()
