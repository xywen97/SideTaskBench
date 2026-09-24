import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_new_duplicate_keys_keep_order(self):
        self.assertEqual(
            solution.append_query("/p", [("k", "1"), ("k", "2"), ("k", "3")]),
            "/p?k=1&k=2&k=3",
        )

    def test_new_blank_values_are_kept(self):
        self.assertEqual(
            solution.append_query("/p", [("empty", ""), ("also", "")]),
            "/p?empty=&also=",
        )

    def test_existing_order_and_duplicates_preserved(self):
        self.assertEqual(
            solution.append_query("/p?b=2&a=1&b=3&empty=", [("c", "x")]),
            "/p?b=2&a=1&b=3&empty=&c=x",
        )

    def test_fragment_and_path_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/a/b?x=1#frag", [("y", "2")]),
            "https://example.test/a/b?x=1&y=2#frag",
        )

    def test_relative_url_without_existing_query(self):
        self.assertEqual(solution.append_query("/a/b", [("x", "1")]), "/a/b?x=1")

    def test_query_only_relative_url(self):
        self.assertEqual(solution.append_query("?a=1", [("b", "2")]), "?a=1&b=2")

    def test_empty_pairs_preserves_existing_query(self):
        self.assertEqual(
            solution.append_query("/p?a=1&a=2&b=", []),
            "/p?a=1&a=2&b=",
        )

    def test_form_encoding_spaces_plus_ampersand_unicode(self):
        self.assertEqual(
            solution.append_query(
                "/p", [("q", "a b"), ("plus", "a+b"), ("amp", "a&b"), ("u", "café")]
            ),
            "/p?q=a+b&plus=a%2Bb&amp=a%26b&u=caf%C3%A9",
        )

    def test_existing_encoded_query_is_normalized_not_lost(self):
        # Equivalent percent-encoding normalization is acceptable; duplicates
        # and blanks must survive a round-trip through urllib.
        self.assertEqual(
            solution.append_query("/p?a=%20&a=2&empty=", [("a", "3")]),
            "/p?a=+&a=2&empty=&a=3",
        )

    def test_accepts_generic_iterable_of_pairs(self):
        pairs = ((k, v) for k, v in [("a", "1"), ("a", "2")])
        self.assertEqual(solution.append_query("/p", pairs), "/p?a=1&a=2")

    def test_url_is_not_mutated_by_caller(self):
        url = "/p?a=1"
        solution.append_query(url, [("a", "2")])
        self.assertEqual(url, "/p?a=1")


if __name__ == "__main__":
    unittest.main()
