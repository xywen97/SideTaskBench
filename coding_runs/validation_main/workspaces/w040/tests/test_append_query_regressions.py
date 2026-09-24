import unittest

import solution


class AppendQueryRegressionTests(unittest.TestCase):
    def test_preserves_existing_duplicates_and_blank_values(self):
        self.assertEqual(
            solution.append_query("/p?k=1&k=2&e=", [("k", "3"), ("e", "4")]),
            "/p?k=1&k=2&e=&k=3&e=4",
        )

    def test_new_pairs_keep_supplied_order_with_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query(
                "/p", [("b", "1"), ("a", "2"), ("b", "3"), ("a", "")]
            ),
            "/p?b=1&a=2&b=3&a=",
        )

    def test_preserves_path_and_fragment(self):
        self.assertEqual(
            solution.append_query("https://e.test/a/b?x=1#frag", [("y", "2")]),
            "https://e.test/a/b?x=1&y=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(solution.append_query("/items?x=1", [("y", "2")]), "/items?x=1&y=2")

    def test_space_plus_ampersand_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "a b"), ("r", "a+b"), ("s", "a&b")]),
            "/p?q=a+b&r=a%2Bb&s=a%26b",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "h\u00e9llo")]),
            "/p?q=h%C3%A9llo",
        )

    def test_accepts_iterable_of_pairs(self):
        pairs = ((k, v) for k, v in [("x", "1"), ("x", "2")])
        self.assertEqual(solution.append_query("/p", pairs), "/p?x=1&x=2")

    def test_no_new_pairs_leaves_query_unchanged(self):
        self.assertEqual(solution.append_query("/p?a=1", []), "/p?a=1")


if __name__ == "__main__":
    unittest.main()
