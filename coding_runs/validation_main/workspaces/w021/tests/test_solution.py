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
            solution.append_query("https://example.test/search", [("b", "2")]),
            "https://example.test/search?b=2",
        )

    def test_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/path?a=1#frag", [("b", "2")]),
            "https://example.test/path?a=1&b=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("relative/path?x=1", [("y", "2")]),
            "relative/path?x=1&y=2",
        )

    def test_new_duplicates_and_blanks_in_order(self):
        self.assertEqual(
            solution.append_query("https://example.test/p", [("a", ""), ("a", ""), ("b", "x")]),
            "https://example.test/p?a=&a=&b=x",
        )

    def test_encoding_spaces_plus_ampersand_unicode(self):
        self.assertEqual(
            solution.append_query("https://example.test/p", [("q", "a b&c+d"), ("u", "caf\u00e9")]),
            "https://example.test/p?q=a+b%26c%2Bd&u=caf%C3%A9",
        )

    def test_existing_encoding_normalized_like_form_data(self):
        # %20 normalizes to '+', while a literal plus stays %2B.
        self.assertEqual(
            solution.append_query("https://example.test/p?a=%20&b=%2B", [("c", "%")]),
            "https://example.test/p?a=+&b=%2B&c=%25",
        )

    def test_pairs_as_generator_consumed_once(self):
        pairs = (p for p in [("a", "1"), ("a", "2")])
        self.assertEqual(
            solution.append_query("https://example.test/p", pairs),
            "https://example.test/p?a=1&a=2",
        )


if __name__ == "__main__":
    unittest.main()
