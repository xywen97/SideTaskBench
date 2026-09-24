import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_appended_duplicates_and_blanks_are_kept(self):
        self.assertEqual(
            solution.append_query("/x", [("a", "1"), ("a", "2"), ("b", "")]),
            "/x?a=1&a=2&b=",
        )

    def test_keeps_existing_duplicates_order_and_blanks(self):
        self.assertEqual(
            solution.append_query("/x?b=1&a=2&b=3&c=", [("a", "4")]),
            "/x?b=1&a=2&b=3&c=&a=4",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://h/p/q?a=1#frag", [("b", "2")]),
            "https://h/p/q?a=1&b=2#frag",
        )

    def test_relative_url_without_query(self):
        self.assertEqual(solution.append_query("/only", [("k", "v")]), "/only?k=v")

    def test_form_encoding_spaces_plus_ampersand(self):
        self.assertEqual(
            solution.append_query("/s", [("q", "a b"), ("r", "c+d"), ("s", "e&f")]),
            "/s?q=a+b&r=c%2Bd&s=e%26f",
        )

    def test_unicode_is_percent_encoded_utf8(self):
        self.assertEqual(
            solution.append_query("/u", [("name", "café")]),
            "/u?name=caf%C3%A9",
        )

    def test_existing_blank_explicit_equals_value(self):
        self.assertEqual(
            solution.append_query("/e?empty=&x=1", [("y", "")]),
            "/e?empty=&x=1&y=",
        )

    def test_no_existing_query_and_no_pairs(self):
        self.assertEqual(solution.append_query("/p", []), "/p")

    def test_pairs_may_be_any_iterable(self):
        self.assertEqual(
            solution.append_query("/g", iter([("a", "1"), ("a", "2")])),
            "/g?a=1&a=2",
        )


if __name__ == "__main__":
    unittest.main()
