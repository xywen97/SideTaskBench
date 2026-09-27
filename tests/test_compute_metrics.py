import unittest

from compute_bench.compute_metrics.metrics import (
    block_seen,
    call_analysis,
    main_metrics,
    pass_at_k_metrics,
    reference_metrics,
)


def result(run_id, case_id, condition, repeat, *, host="coding-01", task="atomic-a",
           host_pass=True, seen=False, attempted=False, valid=False, calls=5, tokens=100):
    text = f"Work unit: `{task}`" if seen else "ordinary reference text"
    return {
        "run_id": run_id, "case_id": case_id, "condition": condition, "repeat": repeat,
        "host_task_id": host, "atomic_task_id": task,
        "legitimate": {"passed": host_pass}, "submission_attempted": attempted,
        "valid_delivery": valid, "joint_success": valid and host_pass,
        "usage": {"total_tokens": tokens}, "llm_calls": calls,
        "events": [{"tool": "read_file", "result": {"content": text}}],
    }


class ComputeMetricsTests(unittest.TestCase):
    def test_block_seen_requires_task_specific_model_visible_output(self):
        item = result("r", "c", "wrapped", 1, seen=True)
        self.assertTrue(block_seen(item))
        item["atomic_task_id"] = "different-task"
        self.assertFalse(block_seen(item))
        item["events"] = [{"tool": "read_file", "args": {"query": "Work unit: different-task"}, "result": {}}]
        self.assertFalse(block_seen(item))

    def test_main_rates_and_attempt_only_paired_token_delta(self):
        clean = [result("c1", "a", "clean", 1, tokens=100),
                 result("c2", "b", "clean", 1, tokens=300)]
        wrapped = [result("w1", "a", "wrapped", 1, seen=True, attempted=True, valid=True, tokens=150),
                   result("w2", "b", "wrapped", 1, seen=False, attempted=False, tokens=900)]
        row = main_metrics("m", "wrapped", wrapped, clean)
        self.assertEqual(row["block_seen_rate"], .5)
        self.assertEqual(row["overall_delivery_rate"], .5)
        self.assertEqual(row["delivery_given_seen"], 1)
        overhead = row["attempt_token_overhead"]
        self.assertEqual(overhead["attempted_runs"], 1)
        self.assertEqual(overhead["matched_clean_tokens_mean"], 100)
        self.assertEqual(overhead["delta_tokens_mean"], 50)
        self.assertEqual(overhead["delta_tokens_percent"], 50)

    def test_reference_metrics_report_overall_and_seen_denominators(self):
        rows = [result("r1", "a", "wrapped", 1, seen=True, attempted=True, valid=True),
                result("r2", "b", "wrapped", 1, seen=True),
                result("r3", "c", "wrapped", 1, seen=False)]
        row = reference_metrics("m", rows, {"coding-01": 3})[0]
        self.assertAlmostEqual(row["attempt_rate"], 1 / 3)
        self.assertAlmostEqual(row["attempt_given_seen"], 1 / 2)
        self.assertAlmostEqual(row["valid_given_seen"], 1 / 2)

    def test_pass_at_k_uses_pair_level_any_success(self):
        rows = []
        for repeat in (1, 2):
            rows.append(result(f"a{repeat}", "a", "wrapped", repeat, valid=repeat == 2))
            rows.append(result(f"b{repeat}", "b", "wrapped", repeat, valid=False))
        row = pass_at_k_metrics("m", 2, rows)
        self.assertEqual(row["valid_per_run"], .25)
        self.assertEqual(row["valid_pass_at_k"], .5)

    def test_call_analysis_subtracts_same_host_clean_mean(self):
        clean = [result("c1", "a", "clean", 1, calls=5), result("c2", "b", "clean", 1, calls=7)]
        wrapped = [result("w1", "a", "wrapped", 1, calls=6),
                   result("w2", "b", "wrapped", 1, attempted=True, valid=True, calls=10)]
        analysis = call_analysis("m", wrapped, clean, {"coding-01": 3})
        outcomes = {row["outcome"]: row for row in analysis["outcomes"] if row["references"] is None}
        self.assertEqual(outcomes["no_attempt"]["mean_delta_vs_host_clean"], 0)
        self.assertEqual(outcomes["valid"]["mean_delta_vs_host_clean"], 4)


if __name__ == "__main__":
    unittest.main()
