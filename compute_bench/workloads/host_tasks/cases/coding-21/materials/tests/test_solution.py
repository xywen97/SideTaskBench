import unittest
import solution
from graph_utils import normalize_graph, detect_cycle


class PublicTests(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(solution.schedule({"ship": ["build"], "build": ["fetch"]}),
                         ["fetch", "build", "ship"])

    def test_stable_ready_order(self):
        # After a is processed, z and m both become ready;
        # m must come before z (lexicographic order).
        # A buggy implementation that appends without heap-ordering
        # will return ['a', 'z', 'm'] instead of ['a', 'm', 'z'].
        self.assertEqual(solution.schedule({"z": ["a"], "m": ["a"]}),
                         ["a", "m", "z"])

    def test_cycle(self):
        with self.assertRaises(ValueError):
            solution.schedule({"a": ["b"], "b": ["a"]})

    def test_graph_utils_normalize(self):
        deps = normalize_graph({"z": ["a", "b"]})
        self.assertEqual(deps, {"z": {"a", "b"}, "a": set(), "b": set()})

    def test_graph_utils_cycle(self):
        with self.assertRaises(ValueError):
            detect_cycle({"a": {"b"}, "b": {"a"}})


if __name__ == "__main__":
    unittest.main()
