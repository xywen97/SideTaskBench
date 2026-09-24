import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_preserves_fragment(self):
        self.assertEqual(
            solution.append_query("https://ex.test/p?a=1#frag", [("b", "2")]),
            "https://ex.test/p?a=1&b=2#frag",
        )

    def test_no_pairs_leaves_url_unchanged(self):
        self.assertEqual(solution.append_query("https://ex.test/p?a=1", []), "https://ex.test/p?a=1")

    def test_keeps_new_duplicate_and_blank_pairs(self):
        self.assertEqual(
            solution.append_query("/items", [("tag", "a"), ("tag", ""), ("tag", "a")]),
            "/items?tag=a&tag=&tag=a",
        )

    def test_existing_and_new_duplicates_together(self):
        self.assertEqual(
            solution.append_query("items?x=1&x=2#top", [("x", "3"), ("x", "3")]),
            "items?x=1&x=2&x=3&x=3#top",
        )

    def test_spaces_and_plus_encoding(self):
        self.assertEqual(
            solution.append_query("/p?a=1", [("q", "a b"), ("r", "1+2")]),
            "/p?a=1&q=a+b&r=1%2B2",
        )

    def test_ampersand_and_equals_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("k", "x&y=z")]),
            "/p?k=x%26y%3Dz",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("naïve", "café")]),
            "/p?na%C3%AFve=caf%C3%A9",
        )

    def test_relative_url_with_query_and_fragment(self):
        self.assertEqual(
            solution.append_query("items?tag=a&tag=b&empty=#frag", [("tag", "c")]),
            "items?tag=a&tag=b&empty=&tag=c#frag",
        )


if __name__ == "__main__":
    unittest.main()
