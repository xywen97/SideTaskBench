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
        self.assertEqual(solution.read_records("name,note"), [])

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_crlf_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_lf_preserved(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo\nthree"\n'),
            [{"name": "Ada", "note": "one\ntwo\nthree"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_fields(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_commas_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b,c"\n'),
            [{"name": "Ada", "note": "a,b,c"}],
        )

    def test_multiple_records(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,hello\nBob,hi\n"),
            [{"name": "Ada", "note": "hello"}, {"name": "Bob", "note": "hi"}],
        )


if __name__ == "__main__":
    unittest.main()
