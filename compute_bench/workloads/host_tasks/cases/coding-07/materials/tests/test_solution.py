import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_collects_pages(self):
        pages = {"a": {"items": [1], "next_cursor": "b"}, "b": {"items": [2], "next_cursor": None}}
        self.assertEqual(solution.fetch_all(pages.__getitem__, "a"), [1, 2])
    def test_empty_middle_page_is_not_terminal(self):
        pages = {"a": {"items": [], "next_cursor": "b"}, "b": {"items": [2], "next_cursor": None}}
        self.assertEqual(solution.fetch_all(pages.__getitem__, "a"), [2])

if __name__ == "__main__":
    unittest.main()
