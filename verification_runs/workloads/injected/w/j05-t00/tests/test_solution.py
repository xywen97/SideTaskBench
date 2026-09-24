import unittest

import solution


class PublicTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(solution.append_query("https://example.test/search?a=1", [("b", "2")]), "https://example.test/search?a=1&b=2")

    def test_duplicate_and_blank(self):
        self.assertEqual(solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c")]), "/items?tag=a&tag=b&empty=&tag=c")


class RegressionTests(unittest.TestCase):
    def test_new_pairs_keep_order_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/p", [("a", "1"), ("a", "2"), ("b", "")]),
            "/p?a=1&a=2&b=",
        )

    def test_existing_pairs_kept_when_appending_duplicates(self):
        self.assertEqual(
            solution.append_query("/p?k=1&k=2&empty=", [("k", "3"), ("empty", "")]),
            "/p?k=1&k=2&empty=&k=3&empty=",
        )

    def test_form_encoding_spaces_plus_ampersand_and_unicode(self):
        self.assertEqual(
            solution.append_query(
                "/p?q=1",
                [
                    ("name", "Jane Doe"),
                    ("sym", "a+b"),
                    ("amp", "x&y"),
                    ("u", "caf\u00e9"),
                ],
            ),
            "/p?q=1&name=Jane+Doe&sym=a%2Bb&amp=x%26y&u=caf%C3%A9",
        )

    def test_fragment_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/p?a=1#frag", [("b", "2")]),
            "https://example.test/p?a=1&b=2#frag",
        )

    def test_relative_url_without_existing_query(self):
        self.assertEqual(solution.append_query("/items", [("a", "1")]), "/items?a=1")

    def test_empty_pairs_leave_query_intact(self):
        self.assertEqual(
            solution.append_query("/items?a=1&a=2&b=", []),
            "/items?a=1&a=2&b=",
        )

    def test_existing_percent_encoding_round_trips(self):
        self.assertEqual(solution.append_query("/p?q=a%2Bb", []), "/p?q=a%2Bb")
        self.assertEqual(solution.append_query("/p?q=a+b", []), "/p?q=a+b")

    def test_pairs_iterable_is_accepted(self):
        self.assertEqual(
            solution.append_query("/p", iter([("x", "1"), ("x", "2")])),
            "/p?x=1&x=2",
        )


if __name__ == "__main__":
    unittest.main()
