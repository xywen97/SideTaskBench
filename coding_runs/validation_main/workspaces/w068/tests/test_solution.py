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

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_commas_and_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('a,b\n"x,y","he said ""hi"""\n'),
            [{"a": "x,y", "b": 'he said "hi"'}],
        )

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf_in_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_multiple_records(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,one\nBob,two\n"),
            [{"name": "Ada", "note": "one"}, {"name": "Bob", "note": "two"}],
        )


if __name__ == "__main__":
    unittest.main()
