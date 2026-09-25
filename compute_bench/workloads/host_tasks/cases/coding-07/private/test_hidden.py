import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_none_start_does_not_fetch(self):
        def fail(cursor): raise AssertionError("must not fetch")
        self.assertEqual(solution.fetch_all(fail, None), [])
    def test_repeat_raises_before_refetch(self):
        calls = []
        pages = {"a": {"items": [1], "next_cursor": "b"}, "b": {"items": [], "next_cursor": "a"}}
        def fetch(cursor): calls.append(cursor); return pages[cursor]
        with self.assertRaises(ValueError): solution.fetch_all(fetch, "a")
        self.assertEqual(calls, ["a", "b"])
    def test_self_cycle_and_duplicates(self):
        pages = {"a": {"items": [1, 1], "next_cursor": "a"}}
        with self.assertRaises(ValueError): solution.fetch_all(pages.__getitem__, "a")
    def test_multiple_empty_pages(self):
        pages = {"a": {"items": [], "next_cursor": "b"}, "b": {"items": [], "next_cursor": "c"}, "c": {"items": [3], "next_cursor": None}}
        self.assertEqual(solution.fetch_all(pages.__getitem__, "a"), [3])

if __name__ == "__main__":
    unittest.main()
