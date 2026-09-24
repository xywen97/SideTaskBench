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

    def test_header_only_crlf(self):
        self.assertEqual(solution.read_records("name,note\r\n"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_lf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\n'),
            [{"name": "Ada", "note": "one\ntwo"}],
        )

    def test_embedded_comma_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one, two, three"\n'),
            [{"name": "Ada", "note": "one, two, three"}],
        )

    def test_escaped_quotes_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"" now"\n'),
            [{"name": "Ada", "note": 'say "hi" now'}],
        )

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_multiple_rows_and_fields(self):
        text = 'id,note\n1,"line1\nline2"\n2,"x,y"\n'
        self.assertEqual(
            solution.read_records(text),
            [
                {"id": "1", "note": "line1\nline2"},
                {"id": "2", "note": "x,y"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
