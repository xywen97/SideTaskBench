import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_existing_order_duplicates_and_blanks_preserved(self):
        self.assertEqual(
            solution.append_query("?a=1&a=2&b=&a=3", []),
            "?a=1&a=2&b=&a=3",
        )

    def test_new_pairs_keep_order_with_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/x", [("k", "v"), ("k", "w"), ("k", "")]),
            "/x?k=v&k=w&k=",
        )

    def test_spaces_plus_and_ampersand_encoded(self):
        self.assertEqual(
            solution.append_query("/s?q=a+b", [("q", "a b+c&d")]),
            "/s?q=a+b&q=a+b%2Bc%26d",
        )

    def test_unicode_encoded_as_utf8(self):
        self.assertEqual(
            solution.append_query("/u", [("x", "café & 日本")]),
            "/u?x=caf%C3%A9+%26+%E6%97%A5%E6%9C%AC",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/p?a=1#section", [("b", "2")]),
            "https://example.test/p?a=1&b=2#section",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("search?x=1", [("y", "2")]),
            "search?x=1&y=2",
        )

    def test_no_existing_query(self):
        self.assertEqual(
            solution.append_query("/path", [("a", "1"), ("b", "")]),
            "/path?a=1&b=",
        )

    def test_accepts_generic_iterable(self):
        self.assertEqual(
            solution.append_query("/x", iter([("k", "v"), ("k", "w")])),
            "/x?k=v&k=w",
        )

    def test_empty_url(self):
        self.assertEqual(solution.append_query("", [("a", "1")]), "?a=1")


if __name__ == "__main__":
    unittest.main()
