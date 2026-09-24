import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_no_existing_query(self):
        self.assertEqual(
            solution.append_query("https://example.test/search", [("a", "1"), ("b", "2")]),
            "https://example.test/search?a=1&b=2",
        )

    def test_new_pairs_preserve_order_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/p", [("x", "1"), ("x", "2"), ("blank", ""), ("x", "3")]),
            "/p?x=1&x=2&blank=&x=3",
        )

    def test_existing_duplicates_and_blanks_preserved(self):
        self.assertEqual(
            solution.append_query("/p?a=1&a=2&b=", [("a", "3")]),
            "/p?a=1&a=2&b=&a=3",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/a/b?x=1#section-2", [("y", "2")]),
            "https://example.test/a/b?x=1&y=2#section-2",
        )

    def test_fragment_without_query(self):
        self.assertEqual(
            solution.append_query("/p#frag", [("y", "2")]),
            "/p?y=2#frag",
        )

    def test_form_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("sp", "a b"), ("plus", "a+b"), ("amp", "a&b")]),
            "/p?sp=a+b&plus=a%2Bb&amp=a%26b",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("word", "caf\u00e9")]),
            "/p?word=caf%C3%A9",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("search?q=1", [("page", "2")]),
            "search?q=1&page=2",
        )

    def test_no_pairs_is_unchanged(self):
        self.assertEqual(solution.append_query("/p?a=1", []), "/p?a=1")

    def test_empty_query_and_no_pairs(self):
        self.assertEqual(solution.append_query("/p", []), "/p")

    def test_dict_pairs_supported(self):
        self.assertEqual(
            solution.append_query("/p?a=1", {"b": "2"}),
            "/p?a=1&b=2",
        )


if __name__ == "__main__":
    unittest.main()
