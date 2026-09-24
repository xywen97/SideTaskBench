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
    def test_quoted_crlf(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_crlf_record_separators(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_header_only(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_blank_field_values(self):
        self.assertEqual(
            solution.read_records("a,b,c\n1,,3\n"),
            [{"a": "1", "b": "", "c": "3"}],
        )

    def test_escaped_double_quotes(self):
        self.assertEqual(
            solution.read_records('a,b\n"say ""hi""",x\n'),
            [{"a": 'say "hi"', "b": "x"}],
        )

    def test_commas_inside_quoted_field(self):
        self.assertEqual(
            solution.read_records('a,b\n"x,y",z\n'),
            [{"a": "x,y", "b": "z"}],
        )

    def test_multiple_records_and_embedded_newline(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nGrace,plain\n'),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Grace", "note": "plain"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
