import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_appends_without_replacing_existing_duplicates(self):
        self.assertEqual(
            solution.append_query("/s?a=1&a=2", [("a", "3")]),
            "/s?a=1&a=2&a=3",
        )

    def test_preserves_blank_values(self):
        self.assertEqual(
            solution.append_query("/s?empty=&flag", [("also", "")]),
            "/s?empty=&flag=&also=",
        )

    def test_supplied_order_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/s?x=1", [("k", "b"), ("k", "a"), ("k", "")]),
            "/s?x=1&k=b&k=a&k=",
        )

    def test_fragment_and_path_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/a/b?x=1#frag", [("y", "2")]),
            "https://example.test/a/b?x=1&y=2#frag",
        )

    def test_no_query_and_no_pairs(self):
        self.assertEqual(solution.append_query("https://example.test/p", []), "https://example.test/p")
        self.assertEqual(solution.append_query("/p", [("a", "")]), "/p?a=")

    def test_form_encoding(self):
        self.assertEqual(
            solution.append_query("/s", [("q", "a b+c&d"), ("u", "\u00e9\u4e2d")]),
            "/s?q=a+b%2Bc%26d&u=%C3%A9%E4%B8%AD",
        )

    def test_accepts_generator(self):
        pairs = ((k, v) for k, v in [("a", "1"), ("a", "2")])
        self.assertEqual(solution.append_query("/s?z=0", pairs), "/s?z=0&a=1&a=2")


if __name__ == "__main__":
    unittest.main()
