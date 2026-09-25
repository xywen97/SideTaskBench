import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(solution.schedule({"ship": ["build"], "build": ["fetch"]}), ["fetch", "build", "ship"])
    def test_stable_ready_order(self):
        self.assertEqual(solution.schedule({"b": ["a"], "a": [], "c": []}), ["a", "b", "c"])
    def test_cycle(self):
        with self.assertRaises(ValueError): solution.schedule({"a": ["b"], "b": ["a"]})

if __name__ == "__main__":
    unittest.main()
