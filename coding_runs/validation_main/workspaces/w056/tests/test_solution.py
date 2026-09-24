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

    def test_commas_quotes_and_blank_fields(self):
        self.assertEqual(
            solution.read_records('name,note,extra\n"A, B","say ""hi""",\n'),
            [{"name": "A, B", "note": 'say "hi"', "extra": ""}],
        )

    def test_header_only(self):
        self.assertEqual(solution.read_records("name,note\n"), [])

    def test_multiple_records_preserving_newlines(self):
        self.assertEqual(
            solution.read_records('name,note\nAda,"one\ntwo"\nBob,plain\n'),
            [
                {"name": "Ada", "note": "one\ntwo"},
                {"name": "Bob", "note": "plain"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
