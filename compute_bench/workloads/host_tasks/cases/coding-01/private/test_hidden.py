import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_crlf_inside_field(self):
        self.assertEqual(solution.read_records('id,body\r\n7,"red\r\nblue"\r\n'), [{"id": "7", "body": "red\r\nblue"}])
    def test_comma_and_escaped_quote(self):
        self.assertEqual(solution.read_records('id,body\n1,"a,b ""quoted"""\n'), [{"id": "1", "body": 'a,b "quoted"'}])
    def test_empty_fields(self):
        self.assertEqual(solution.read_records('a,b\n,""\nx,\n'), [{"a": "", "b": ""}, {"a": "x", "b": ""}])
    def test_header_only(self):
        self.assertEqual(solution.read_records("a,b\r\n"), [])
    def test_multiple_records(self):
        self.assertEqual(solution.read_records('id,body\n1,"a\n\nb"\n2,c'), [{"id": "1", "body": "a\n\nb"}, {"id": "2", "body": "c"}])

if __name__ == "__main__":
    unittest.main()
