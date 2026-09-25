import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_dependency_only_and_duplicates(self):
        graph = {"z": ["a", "a", "b"]}
        self.assertEqual(solution.schedule(graph), ["a", "b", "z"])
        self.assertEqual(graph, {"z": ["a", "a", "b"]})
    def test_dynamic_lexicographic_choice(self):
        self.assertEqual(solution.schedule({"d": ["b"], "c": ["a"]}), ["a", "b", "c", "d"])
    def test_self_loop(self):
        with self.assertRaises(ValueError): solution.schedule({"a": ["a"]})
    def test_empty(self):
        self.assertEqual(solution.schedule({}), [])
    def test_iterable_dependencies(self):
        self.assertEqual(solution.schedule({"b": iter(["a"])}), ["a", "b"])

if __name__ == "__main__":
    unittest.main()
