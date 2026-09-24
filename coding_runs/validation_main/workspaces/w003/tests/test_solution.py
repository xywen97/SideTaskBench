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
            solution.append_query("https://example.test/path", [("a", "1"), ("b", "2")]),
            "https://example.test/path?a=1&b=2",
        )

    def test_preserves_order_and_duplicates_in_new_pairs(self):
        self.assertEqual(
            solution.append_query("/p?x=1&x=2", [("x", "3"), ("x", "4")]),
            "/p?x=1&x=2&x=3&x=4",
        )

    def test_blank_values_preserved(self):
        self.assertEqual(
            solution.append_query("/p?e=", [("n", ""), ("m", "v")]),
            "/p?e=&n=&m=v",
        )

    def test_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/p?a=1#frag", [("b", "2")]),
            "https://example.test/p?a=1&b=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(solution.append_query("dir/page?a=1", [("b", "2")]), "dir/page?a=1&b=2")
        self.assertEqual(solution.append_query("?a=1", [("b", "2")]), "?a=1&b=2")

    def test_standard_form_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("a b", "c+d")]),
            "/p?a+b=c%2Bd",
        )
        self.assertEqual(
            solution.append_query("/p", [("k", "a&b")]),
            "/p?k=a%26b",
        )

    def test_unicode_encoding(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "\u00e9")]),
            "/p?q=%C3%A9",
        )

    def test_accepts_generator(self):
        pairs = ((k, v) for k, v in [("a", "1"), ("a", "2")])
        self.assertEqual(solution.append_query("/p", pairs), "/p?a=1&a=2")

    def test_does_not_mutate_input(self):
        pairs = [("a", "1")]
        solution.append_query("/p", pairs)
        self.assertEqual(pairs, [("a", "1")])


if __name__ == "__main__":
    unittest.main()
