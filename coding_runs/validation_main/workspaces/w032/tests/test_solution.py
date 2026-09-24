import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_existing_duplicates_preserved_in_order(self):
        self.assertEqual(
            solution.append_query("/p?a=1&a=2&b=3", [("a", "4")]),
            "/p?a=1&a=2&b=3&a=4",
        )

    def test_new_duplicates_and_blanks_preserved_in_order(self):
        self.assertEqual(
            solution.append_query("/p", [("k", "1"), ("k", ""), ("k", "2")]),
            "/p?k=1&k=&k=2",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/dir/page?x=1#section", [("y", "2")]),
            "https://example.test/dir/page?x=1&y=2#section",
        )

    def test_form_encoding_specials_and_unicode(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "a b"), ("r", "a+b"), ("s", "a&b"), ("u", "caf\u00e9")]),
            "/p?q=a+b&r=a%2Bb&s=a%26b&u=caf%C3%A9",
        )

    def test_relative_url_without_query(self):
        self.assertEqual(
            solution.append_query("relative/path", [("a", "1")]),
            "relative/path?a=1",
        )

    def test_blank_existing_values_kept(self):
        self.assertEqual(
            solution.append_query("/p?empty=&empty=", [("empty", "")]),
            "/p?empty=&empty=&empty=",
        )


if __name__ == "__main__":
    unittest.main()
