import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")
    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_preserves_existing_order_and_duplicates(self):
        self.assertEqual(
            solution.append_query("/p?a=1&b=2&a=3", []),
            "/p?a=1&b=2&a=3",
        )

    def test_new_pairs_keep_supplied_order_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/p", [("k", ""), ("k", ""), ("k", "v")]),
            "/p?k=&k=&k=v",
        )

    def test_encoding_of_spaces_plus_ampersand_and_unicode(self):
        self.assertEqual(
            solution.append_query(
                "https://ex.test/p",
                [("q", "a b"), ("r", "a+b"), ("s", "a&b"), ("u", "caf\u00e9")],
            ),
            "https://ex.test/p?q=a+b&r=a%2Bb&s=a%26b&u=caf%C3%A9",
        )

    def test_path_and_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://ex.test/a/b?x=1#frag", [("y", "2")]),
            "https://ex.test/a/b?x=1&y=2#frag",
        )

    def test_relative_url(self):
        self.assertEqual(
            solution.append_query("/relative/path", [("n", "1"), ("n", "2")]),
            "/relative/path?n=1&n=2",
        )

    def test_accepts_generator_of_pairs(self):
        pairs = (("n", str(i)) for i in range(3))
        self.assertEqual(
            solution.append_query("/p", pairs),
            "/p?n=0&n=1&n=2",
        )


if __name__ == "__main__":
    unittest.main()
