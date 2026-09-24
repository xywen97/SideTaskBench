import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")

    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_new_duplicates_and_blanks_in_order(self):
        self.assertEqual(
            solution.append_query("/p", [("k", "1"), ("k", "2"), ("b", "")]),
            "/p?k=1&k=2&b=",
        )

    def test_existing_duplicates_blank_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query(
                "https://h.test/path?a=1&a=2&b=#frag", [("a", "3")]
            ),
            "https://h.test/path?a=1&a=2&b=&a=3#frag",
        )

    def test_no_existing_query(self):
        self.assertEqual(
            solution.append_query("https://h.test/path", [("x", "y")]),
            "https://h.test/path?x=y",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("rel/path?z=9", [("y", "8")]),
            "rel/path?z=9&y=8",
        )

    def test_space_plus_ampersand_unicode_encoding(self):
        self.assertEqual(
            solution.append_query(
                "/s",
                [("q", "a b"), ("q", "c+d"), ("q", "e&f"), ("q", "\u00e9\u4e2d")],
            ),
            "/s?q=a+b&q=c%2Bd&q=e%26f&q=%C3%A9%E4%B8%AD",
        )

    def test_iterator_pairs_consumed(self):
        pairs = ((k, v) for k, v in [("a", "1"), ("a", "2")])
        self.assertEqual(solution.append_query("/p", pairs), "/p?a=1&a=2")

    def test_empty_pairs(self):
        self.assertEqual(solution.append_query("/p?x=1", []), "/p?x=1")

    def test_mapping_pairs_supported(self):
        self.assertEqual(
            solution.append_query("/p", {"a": "1", "b": "2"}), "/p?a=1&b=2"
        )


if __name__ == "__main__":
    unittest.main()
