import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")

if __name__ == "__main__":
    unittest.main()
