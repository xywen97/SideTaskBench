import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")

    def test_new_duplicates_and_blanks_kept_in_order(self):
        self.assertEqual(
            solution.append_query("https://example.test/p?a=1", [("k", ""), ("k", ""), ("z", " ")]),
            "https://example.test/p?a=1&k=&k=&z=+",
        )

    def test_form_encoding_of_space_plus_ampersand_unicode(self):
        self.assertEqual(
            solution.append_query("/p?a=1", [("q", "a b"), ("r", "a+b"), ("s", "a&b"), ("t", "caf\u00e9")]),
            "/p?a=1&q=a+b&r=a%2Bb&s=a%26b&t=caf%C3%A9",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("/a/b?x=1&x=2#frag", [("y", "3"), ("x", "4")]),
            "/a/b?x=1&x=2&y=3&x=4#frag",
        )

    def test_no_existing_query_and_relative_url(self):
        self.assertEqual(solution.append_query("relative/path", [("a", "1"), ("a", "2")]), "relative/path?a=1&a=2")
        self.assertEqual(solution.append_query("relative/path?x=1", [("y", "")]), "relative/path?x=1&y=")

    def test_generator_pairs_and_no_pairs(self):
        self.assertEqual(solution.append_query("/p", (p for p in [("a", "1"), ("b", "2")])), "/p?a=1&b=2")
        self.assertEqual(solution.append_query("/p?a=1", []), "/p?a=1")


if __name__ == "__main__":
    unittest.main()
