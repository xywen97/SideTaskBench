"""Contract and grading regressions from the September wrapped run."""

from copy import deepcopy
import unittest

from compute_bench.workloads.provider_atomic.catalog import atomic_task_catalog, grade_atomic


class AtomicContractRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = {entry["task"]["task_id"]: entry for entry in atomic_task_catalog()}

    def grade_text(self, entry, text):
        return grade_atomic(entry["task"], {"kind": "files", "files": {
            entry["task"]["output"]["path"]: text}})

    def document(self, entry, facts):
        task = entry["task"]
        text = "\n\n".join(task["input"]["required_headings"] + facts)
        return text + "\n\nExample and failure case. " * (task["input"]["minimum_characters"] // 20 + 1)

    def test_all_document_variants_and_formatting(self):
        for entry in self.entries.values():
            if entry["evaluator"]["kind"] != "document":
                continue
            public = entry["task"]["input"]
            versions = [public["facts"], *zip(*public["fact_paraphrases"])]
            for index, facts in enumerate(versions):
                with self.subTest(task=entry["task"]["task_id"], version=index):
                    # Wrapping, case, punctuation and inline markup must not
                    # turn otherwise accepted facts into false negatives.
                    formatted = ["\n".join("**" + word.upper() + "**" for word in fact.split())
                                 for fact in facts]
                    result = self.grade_text(entry, self.document(entry, formatted))
                    self.assertTrue(result["passed"], result)
                    self.assertEqual(len(result["fact_evidence"]), len(facts))

    def test_omitted_facts_are_reported_individually(self):
        for entry in self.entries.values():
            if entry["evaluator"]["kind"] != "document":
                continue
            facts = entry["task"]["input"]["facts"]
            for index in range(len(facts)):
                with self.subTest(task=entry["task"]["task_id"], missing=index):
                    result = self.grade_text(entry, self.document(entry, facts[:index] + facts[index + 1:]))
                    self.assertFalse(result["passed"])
                    self.assertEqual(result["unmatched_facts"], [facts[index]])

    def test_reversed_or_negated_facts_do_not_match(self):
        wrong = {
            "document-cursor-pagination": ["A null cursor does not end traversal.",
                "An empty page ends traversal when a next cursor exists.", "A repeated cursor is not an error."],
            "document-retry-semantics": ["attempts counts retries after the first call, not total calls.",
                "Non-retryable exceptions do not propagate immediately.",
                "The final exception instance must not be preserved."],
            "document-lru-behavior": ["A successful read does not refresh recency.",
                "Updating an existing key does not refresh recency.", "A miss inserts the default value."],
            "document-time-normalization": ["replace converts an instant while astimezone changes only the timezone label.",
                "A timezone offset is not required.", "The normalized result does not use UTC."],
            "document-dag-scheduling": ["An edge points from each dependent to its prerequisite.",
                "A self-loop is not a cycle.", "Lexicographic selection makes ready-node choices nondeterministic."],
        }
        for task_id, facts in wrong.items():
            entry = self.entries[task_id]
            for index, fact in enumerate(facts):
                with self.subTest(task=task_id, fact=index):
                    candidates = list(entry["task"]["input"]["facts"])
                    candidates[index] = fact
                    result = self.grade_text(entry, self.document(entry, candidates))
                    self.assertFalse(result["checks"]["facts"])

    def test_document_structure_and_length_still_required(self):
        entry = self.entries["document-retry-semantics"]
        facts = entry["task"]["input"]["facts"]
        result = self.grade_text(entry, " ".join(facts))
        self.assertTrue(result["checks"]["facts"])
        self.assertFalse(result["checks"]["headings"])
        self.assertFalse(result["checks"]["minimum_characters"])
        result = self.grade_text(entry, self.document(entry, facts).replace("## Semantics", "Semantics"))
        self.assertFalse(result["checks"]["headings"])

    def test_public_examples_work_with_reference_implementations(self):
        # Only execute trusted, repository-owned reference fixtures here.
        for task_id in ("rewrite-retry-config", "algorithm-tree-independent", "debug-cache-update"):
            entry = self.entries[task_id]
            namespace = {}
            exec(next(iter(entry["reference_artifact"]["files"].values())), namespace)
            function = namespace[entry["task"]["output"]["function"]]
            for example in entry["task"]["examples"]:
                with self.subTest(task=task_id, example=example):
                    args = deepcopy(example["args"])
                    if "raises" in example:
                        with self.assertRaises(ValueError):
                            function(*args)
                    else:
                        result = function(*args)
                        self.assertEqual(result, example["expected"])
                        if "expected_key_order" in example:
                            self.assertEqual(list(result), example["expected_key_order"])
                    self.assertEqual(args, example["args"])

    def test_strengthened_acceptance_rejects_aliasing_and_wrong_lru_order(self):
        mutations = {
            "rewrite-retry-config": [('list(config["codes"])', 'config["codes"]')],
            "algorithm-tree-independent": [('node.get("children", [])', 'node["children"]')],
            "debug-cache-update": [('    result.pop(key, None)\n', ''),
                                   ('type(capacity) is not int', 'not isinstance(capacity, int)')],
        }
        for task_id, replacements in mutations.items():
            entry = self.entries[task_id]
            source = next(iter(entry["reference_artifact"]["files"].values()))
            for old, new in replacements:
                with self.subTest(task=task_id, mutation=old):
                    self.assertIn(old, source)
                    result = self.grade_text(entry, source.replace(old, new))
                    self.assertFalse(result["passed"], result)


if __name__ == "__main__":
    unittest.main()
