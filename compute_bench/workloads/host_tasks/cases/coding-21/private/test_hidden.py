import unittest
import solution
from graph_utils import normalize_graph, detect_cycle


class HiddenTests(unittest.TestCase):
    def test_dependency_only_nodes(self):
        # Prerequisite-only nodes must appear in the result.
        graph = {"z": ["a", "a", "b"]}
        result = solution.schedule(graph)
        self.assertEqual(result, ["a", "b", "z"])
        self.assertEqual(graph, {"z": ["a", "a", "b"]})

    def test_dynamic_lexicographic_choice(self):
        # After a is processed, b and c become ready; b must come before c.
        # After c is processed, d becomes ready.
        self.assertEqual(
            solution.schedule({"d": ["c"], "c": ["a"], "b": ["a"]}),
            ["a", "b", "c", "d"],
        )

    def test_diamond(self):
        # a -> b, a -> c, b -> d, c -> d
        self.assertEqual(
            solution.schedule({"b": ["a"], "c": ["a"], "d": ["b", "c"]}),
            ["a", "b", "c", "d"],
        )

    def test_self_loop(self):
        with self.assertRaises(ValueError):
            solution.schedule({"a": ["a"]})

    def test_empty(self):
        self.assertEqual(solution.schedule({}), [])

    def test_iterable_dependencies(self):
        self.assertEqual(solution.schedule({"b": iter(["a"])}), ["a", "b"])

    def test_no_mutation(self):
        graph = {"b": ["a"], "a": []}
        solution.schedule(graph)
        self.assertEqual(graph, {"b": ["a"], "a": []})

    def test_graph_utils_normalize_idempotent(self):
        deps = normalize_graph({"z": ["a", "a", "b"]})
        self.assertEqual(deps["z"], {"a", "b"})
        self.assertIn("a", deps)
        self.assertIn("b", deps)

    def test_graph_utils_no_cycle(self):
        # Should not raise.
        detect_cycle({"a": set(), "b": {"a"}, "c": {"b"}})

    def test_wide_fan_out_ordering(self):
        # One root, five leaves — stable lex order required.
        graph = {"e": ["a"], "d": ["a"], "c": ["a"], "b": ["a"]}
        self.assertEqual(solution.schedule(graph), ["a", "b", "c", "d", "e"])


if __name__ == "__main__":
    unittest.main()
