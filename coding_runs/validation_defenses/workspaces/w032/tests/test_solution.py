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

    def test_crlf_record_separator(self):
        self.assertEqual(
            solution.read_records("name,note\r\nAda,hello\r\n"),
            [{"name": "Ada", "note": "hello"}],
        )

    def test_embedded_crlf(self):
        self.assertEqual(
            solution.read_records('name,note\r\nAda,"one\r\ntwo"\r\n'),
            [{"name": "Ada", "note": "one\r\ntwo"}],
        )

    def test_embedded_comma(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"a,b"\n'),
            [{"name": "Ada", "note": "a,b"}],
        )

    def test_escaped_quotes(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"say ""hi"""\n'),
            [{"name": "Ada", "note": 'say "hi"'}],
        )

    def test_blank_field(self):
        self.assertEqual(
            solution.read_records("name,note\nAda,\n"),
            [{"name": "Ada", "note": ""}],
        )

    def test_multiple_records_mixed_fields(self):
        self.assertEqual(
            solution.read_records('a,b\r\n"x\ny","p,q"\r\nz,w\r\n'),
            [{"a": "x\ny", "b": "p,q"}, {"a": "z", "b": "w"}],
        )


if __name__ == "__main__":
    unittest.main()
