import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_preserves_fragment_and_path(self):
        self.assertEqual(
            solution.append_query("https://example.test/a/b?a=1#frag", [("b", "2")]),
            "https://example.test/a/b?a=1&b=2#frag",
        )

    def test_fragment_only_url(self):
        self.assertEqual(
            solution.append_query("https://example.test/p#frag", [("a", "1")]),
            "https://example.test/p?a=1#frag",
        )

    def test_new_pairs_keep_order_and_duplicates(self):
        self.assertEqual(
            solution.append_query("https://example.test/p?a=1", [("b", "2"), ("b", "3")]),
            "https://example.test/p?a=1&b=2&b=3",
        )

    def test_blank_values_preserved(self):
        self.assertEqual(
            solution.append_query("/rel?empty=&a=", [("empty2", ""), ("a", "2")]),
            "/rel?empty=&a=&empty2=&a=2",
        )

    def test_relative_url_without_query(self):
        self.assertEqual(solution.append_query("/rel", [("y", "")]), "/rel?y=")

    def test_empty_pairs_no_trailing_separator(self):
        self.assertEqual(solution.append_query("/rel?x=1", []), "/rel?x=1")
        self.assertEqual(solution.append_query("/rel", []), "/rel")

    def test_form_encoding_of_special_characters(self):
        self.assertEqual(
            solution.append_query(
                "https://example.test/p?a=1",
                [("sp", "a b"), ("plus", "a+b"), ("amp", "a&b"), ("uni", "caf\u00e9")],
            ),
            "https://example.test/p?a=1&sp=a+b&plus=a%2Bb&amp=a%26b&uni=caf%C3%A9",
        )

    def test_accepts_generic_iterable(self):
        pairs = (pair for pair in [("k", "v"), ("k", "w")])
        self.assertEqual(solution.append_query("/rel", pairs), "/rel?k=v&k=w")


if __name__ == "__main__":
    unittest.main()
