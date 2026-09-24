import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_new_pairs_preserve_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/x", [("a", "1"), ("a", "2"), ("b", "")]),
            "/x?a=1&a=2&b=",
        )

    def test_no_existing_query(self):
        self.assertEqual(
            solution.append_query("https://e.test/p", [("k", "v")]),
            "https://e.test/p?k=v",
        )

    def test_relative_url_with_fragment(self):
        self.assertEqual(
            solution.append_query("/a/b?x=1#frag", [("y", "2")]),
            "/a/b?x=1&y=2#frag",
        )

    def test_path_and_fragment_preserved_without_query(self):
        self.assertEqual(
            solution.append_query("/a/b#frag", [("y", "2")]),
            "/a/b?y=2#frag",
        )

    def test_form_encoding_of_special_characters(self):
        self.assertEqual(
            solution.append_query("/s", [("q", "a b+c&d")]),
            "/s?q=a+b%2Bc%26d",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/s", [("q", "caf\u00e9")]),
            "/s?q=caf%C3%A9",
        )

    def test_empty_pairs_returns_original(self):
        self.assertEqual(
            solution.append_query("/p?a=1#f", []),
            "/p?a=1#f",
        )


if __name__ == "__main__":
    unittest.main()
