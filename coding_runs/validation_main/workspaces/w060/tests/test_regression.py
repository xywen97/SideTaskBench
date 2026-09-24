import unittest

import solution


class AppendQueryRegressionTests(unittest.TestCase):
    def test_preserves_existing_order_duplicates_and_blanks(self):
        self.assertEqual(
            solution.append_query("/items?tag=a&tag=b&empty=", [("tag", "c"), ("empty", "")]),
            "/items?tag=a&tag=b&empty=&tag=c&empty=",
        )

    def test_new_pairs_keep_supplied_order_with_duplicates(self):
        self.assertEqual(
            solution.append_query("/p?x=1", [("k", "1"), ("k", "2"), ("j", "3")]),
            "/p?x=1&k=1&k=2&j=3",
        )

    def test_path_and_fragment_are_preserved(self):
        self.assertEqual(
            solution.append_query("https://example.test/a/b?x=1#section", [("y", "2")]),
            "https://example.test/a/b?x=1&y=2#section",
        )

    def test_form_encoding_of_spaces_plus_and_ampersands(self):
        self.assertEqual(
            solution.append_query(
                "https://example.test/search?q=a b", [("r", "c+d&e")],
            ),
            "https://example.test/search?q=a+b&r=c%2Bd%26e",
        )

    def test_unicode_is_percent_encoded(self):
        self.assertEqual(
            solution.append_query("/p", [("q", "caf\u00e9")]),
            "/p?q=caf%C3%A9",
        )

    def test_relative_url_without_existing_query(self):
        self.assertEqual(
            solution.append_query("./a/b", [("k", "v")]),
            "./a/b?k=v",
        )

    def test_empty_pairs_preserve_existing_query(self):
        self.assertEqual(
            solution.append_query("/p?a=1&a=&b=2", []),
            "/p?a=1&a=&b=2",
        )


if __name__ == "__main__":
    unittest.main()
