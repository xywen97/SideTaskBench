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
    def test_lf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,hello\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_lf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\n'),
            [{"name": "Ada", "note": "one\ntwo"}],
        )

    def test_embedded_crlf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_crlf_in_lf_record(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\r\ntwo"\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_commas_escaped_quotes_and_blank_fields(self):
        self.assertEqual(
            solution.read_records('a,b,c\n"x, y","he said ""hi""",\n'),
            [{"a": "x, y", "b": 'he said "hi"', "c": ""}],
        )

    def test_header_only_returns_empty(self):
        self.assertEqual(solution.read_records("a,b\n"), [])
        self.assertEqual(solution.read_records("a,b\r\n"), [])

    def test_multiple_multiline_records(self):
        self.assertEqual(
            solution.read_records('a,b\n1,"x\ny"\n2,"\r\n"\n'),
            [{"a": "1", "b": "x\ny"}, {"a": "2", "b": "\r\n"}],
        )


if __name__ == "__main__":
    unittest.main()
