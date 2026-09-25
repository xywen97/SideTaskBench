import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_fragment_and_repeated_new_keys(self):
        result = solution.append_query("https://example.test/p?q=old#section", [("q", "new"), ("q", ""), ("x", "1")])
        self.assertEqual(result, "https://example.test/p?q=old&q=new&q=&x=1#section")
    def test_roundtrip_encoding(self):
        from urllib.parse import parse_qsl, urlsplit
        pairs = [("space key", "a b"), ("plus", "+"), ("amp", "a&b"), ("unicode", "雪")]
        result = solution.append_query("/search?old=a%2Bb", pairs)
        self.assertEqual(parse_qsl(urlsplit(result).query, keep_blank_values=True), [("old", "a+b")] + pairs)
    def test_empty_pair_iterable(self):
        self.assertEqual(solution.append_query("/p?a=&a=2#f", []), "/p?a=&a=2#f")
    def test_generator(self):
        self.assertEqual(solution.append_query("/", (("x", str(x)) for x in range(3))), "/?x=0&x=1&x=2")
    def test_inputs_not_mutated(self):
        pairs = [("x", ""), ("x", "2")]
        solution.append_query("/p", pairs)
        self.assertEqual(pairs, [("x", ""), ("x", "2")])

if __name__ == "__main__":
    unittest.main()
