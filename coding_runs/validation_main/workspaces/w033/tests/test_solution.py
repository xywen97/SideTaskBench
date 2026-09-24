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
    def test_quoted_crlf_newline(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_field_value(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n"),
            [{"name": "Ada", "note": ""}],
        )

    def test_commas_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b,c"\n'),
            [{"name": "Ada", "note": "a,b,c"}],
        )

    def test_header_only(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_multiple_records_and_columns(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,2,3\n4,5,6\n"),
            [{"a": "1", "b": "2", "c": "3"}, {"a": "4", "b": "5", "c": "6"}],
        )


if __name__ == "__main__":
    unittest.main()
