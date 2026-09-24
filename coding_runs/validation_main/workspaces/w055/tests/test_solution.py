import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.load_jsonl('{"id":1}\n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_blank_lines(self):
        self.assertEqual(solution.load_jsonl('\n{"id":1}\n  \n{"id":2}\n'), [{"id": 1}, {"id": 2}])
    def test_empty(self):
        self.assertEqual(solution.load_jsonl(" \n\t"), [])


class RegressionTests(unittest.TestCase):
    def test_nonblank_invalid_json_reports_physical_line(self):
        text = '{"id":1}\n\n{oops}\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertEqual(str(ctx.exception).split(":")[0], "line 3")

    def test_non_object_reports_physical_line(self):
        text = '[1, 2]\n[3]\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertEqual(str(ctx.exception).split(":")[0], "line 1")

    def test_leading_blank_offsets_line_number(self):
        text = '\n\n   \nnot json\n'
        with self.assertRaises(ValueError) as ctx:
            solution.load_jsonl(text)
        self.assertEqual(str(ctx.exception).split(":")[0], "line 4")

    def test_order_preserved(self):
        text = '{"a":1}\n{"b":2}\n{"a":3}\n'
        self.assertEqual(solution.load_jsonl(text), [{"a": 1}, {"b": 2}, {"a": 3}])

    def test_no_final_newline(self):
        self.assertEqual(solution.load_jsonl('{"x":1}'), [{"x": 1}])


if __name__ == "__main__":
    unittest.main()
