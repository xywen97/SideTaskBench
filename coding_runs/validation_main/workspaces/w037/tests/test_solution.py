import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_new_duplicate_pairs_keep_order(self):
        self.assertEqual(
            solution.append_query("/p", [("a", "1"), ("a", "2")]),
            "/p?a=1&a=2",
        )

    def test_new_blank_value_is_kept(self):
        self.assertEqual(solution.append_query("/p", [("a", "")]), "/p?a=")
        self.assertEqual(solution.append_query("/p", [("a", ""), ("b", "")]), "/p?a=&b=")

    def test_existing_blank_and_duplicates_preserved(self):
        self.assertEqual(
            solution.append_query("/p?x=1&x=2&blank=&y=", []),
            "/p?x=1&x=2&blank=&y=",
        )

    def test_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("/p?x=1#frag", [("y", "2")]),
            "/p?x=1&y=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(solution.append_query("items?a=1", [("b", "2")]), "items?a=1&b=2")
        self.assertEqual(solution.append_query("items", [("a", "1")]), "items?a=1")

    def test_form_encoding(self):
        self.assertEqual(
            solution.append_query(
                "/p",
                [("q", "a b"), ("r", "1+2"), ("s", "x&y"), ("t", "\u00fc")],
            ),
            "/p?q=a+b&r=1%2B2&s=x%26y&t=%C3%BC",
        )

    def test_pairs_accept_arbitrary_iterable(self):
        self.assertEqual(
            solution.append_query("/p", (pair for pair in [("a", "1"), ("a", "1")])),
            "/p?a=1&a=1",
        )


if __name__ == "__main__":
    unittest.main()
