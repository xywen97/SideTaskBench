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
            solution.append_query("https://example.test/search", [("a", "1")]),
            "https://example.test/search?a=1",
        )

    def test_empty_pairs_preserves_existing_query(self):
        self.assertEqual(
            solution.append_query("/items?tag=a&tag=b&empty=", []),
            "/items?tag=a&tag=b&empty=",
        )

    def test_duplicate_new_pairs_preserved_in_order(self):
        self.assertEqual(
            solution.append_query("/p?k=0", [("k", "1"), ("k", "2")]),
            "/p?k=0&k=1&k=2",
        )

    def test_blank_new_value(self):
        self.assertEqual(
            solution.append_query("/p?a=1", [("empty", "")]),
            "/p?a=1&empty=",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("/path/sub?x=1#frag", [("y", "2")]),
            "/path/sub?x=1&y=2#frag",
        )

    def test_fragment_without_query(self):
        self.assertEqual(
            solution.append_query("/path#frag", [("y", "2")]),
            "/path?y=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("items?x=1", [("y", "2")]),
            "items?x=1&y=2",
        )

    def test_form_encoding_spaces_plus_ampersand(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "a b"), ("r", "a+b"), ("s", "a&b")]),
            "/p?q=a+b&r=a%2Bb&s=a%26b",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "caf\u00e9")]),
            "/p?q=caf%C3%A9",
        )

    def test_existing_pair_order_and_duplicates_kept(self):
        self.assertEqual(
            solution.append_query("/p?a=1&b=2&a=3", [("c", "4")]),
            "/p?a=1&b=2&a=3&c=4",
        )


if __name__ == "__main__":
    unittest.main()
