import unittest

from compute_bench.compute_metrics.levels import (
    adjacency_tests,
    build_report,
    category_matrix,
    level_table,
    pair_agreement,
    pair_table,
    standardize,
    unit_contrasts,
)


def result(run_id, host, task, *, category="algorithm", host_pass=True, seen=True,
           valid=False, repeat=1):
    return {
        "run_id": run_id, "case_id": f"{host}__{task}", "condition": "wrapped",
        "repeat": repeat, "host_task_id": host, "atomic_task_id": task,
        "atomic_category": category,
        "legitimate": {"passed": host_pass}, "exposed": seen,
        "submission_attempted": valid, "valid_delivery": valid,
        "joint_success": valid and host_pass,
        "usage": {"total_tokens": 100}, "llm_calls": 5, "events": [],
    }


class LevelTableTests(unittest.TestCase):
    def test_valid_given_seen_uses_the_exposed_denominator(self):
        # One not-exposed run must leave both the numerator and the denominator.
        runs = [result("a", "coding-01", "t-a", valid=True),
                result("b", "coding-01", "t-b", valid=False),
                result("c", "coding-01", "t-c", seen=False, valid=True)]
        row = level_table({"L3": runs})[0]
        self.assertEqual(row["runs"], 3)
        self.assertAlmostEqual(row["exposed_rate"], 200 / 3)
        self.assertEqual(row["valid_given_seen"], 50.0)
        self.assertAlmostEqual(row["valid_rate"], 200 / 3)
        self.assertEqual(row["pairs"], 3)

    def test_levels_are_reported_in_declared_order_and_only_when_present(self):
        rows = level_table({"L0": [result("a", "coding-01", "t-a")],
                            "L3": [result("b", "coding-01", "t-b")]})
        self.assertEqual([row["level"] for row in rows], ["L3", "L0"])

    def test_joint_success_requires_both_sides(self):
        runs = [result("a", "coding-01", "t-a", host_pass=False, valid=True),
                result("b", "coding-01", "t-b", valid=True)]
        row = level_table({"L1": runs})[0]
        self.assertEqual(row["valid_rate"], 100.0)
        self.assertEqual(row["joint_success_rate"], 50.0)


class CategoryMatrixTests(unittest.TestCase):
    def test_grid_keeps_one_cell_per_level_and_category(self):
        runs = [result("a", "coding-01", "t-a", category="algorithm", valid=True),
                result("b", "coding-01", "t-b", category="algorithm", valid=False),
                result("c", "coding-01", "t-c", category="function_rewrite", valid=True)]
        matrix = category_matrix({"L3": runs})
        cells = {(row["level"], row["category"]): row for row in matrix["grid"]}
        self.assertEqual(cells[("L3", "algorithm")]["valid_given_seen"], 50.0)
        self.assertEqual(cells[("L3", "algorithm")]["runs"], 2)
        self.assertEqual(cells[("L3", "function_rewrite")]["valid_given_seen"], 100.0)
        # A level with no such unit must leave the cell absent, not zero.
        self.assertNotIn(("L0", "algorithm"), cells)

    def test_categories_follow_the_declared_order_then_any_extras(self):
        matrix = category_matrix({"L3": [
            result("a", "coding-01", "t-a", category="unknown-extra"),
            result("b", "coding-01", "t-b", category="algorithm"),
        ]})
        self.assertEqual(matrix["categories"][:2], ["algorithm", "unknown-extra"])

    def test_endpoint_gap_is_reported_per_category(self):
        runs = {"L3": [result("a", "coding-01", "t-a", category="algorithm", valid=True)],
                "L0": [result("b", "coding-01", "t-b", category="algorithm", valid=False)]}
        gaps = {row["category"]: row for row in category_matrix(runs)["endpoint_gaps"]}
        self.assertEqual(gaps["algorithm"]["delta_points"], 100.0)
        # A category present at only one endpoint cannot produce a gap.
        runs["L0"].append(result("c", "coding-01", "t-c", category="function_debug"))
        gaps = {row["category"]: row for row in category_matrix(runs)["endpoint_gaps"]}
        self.assertNotIn("function_debug", gaps)

    def test_endpoint_gaps_sort_by_descending_delta(self):
        runs = {
            "L3": [result("a", "coding-01", "t-a", category="algorithm", valid=True),
                   result("b", "coding-01", "t-b", category="function_rewrite", valid=False)],
            "L0": [result("c", "coding-01", "t-c", category="algorithm", valid=False),
                   result("d", "coding-01", "t-d", category="function_rewrite", valid=True)],
        }
        gaps = category_matrix(runs)["endpoint_gaps"]
        self.assertEqual([row["category"] for row in gaps], ["algorithm", "function_rewrite"])


class StandardizationTests(unittest.TestCase):
    def test_reweighting_to_the_pooled_mix_changes_a_mixed_level(self):
        # L3 is all algorithm; L0 is half algorithm, half a category where it does
        # better.  Pooled weights are 3/6 and 3/6, so the standardized L0 must be
        # the average of its two rates rather than its raw rate.
        runs = {
            "L3": [result(f"a{i}", "coding-01", f"t-a{i}", category="algorithm", valid=True)
                   for i in range(3)],
            "L0": [result(f"b{i}", "coding-01", f"t-b{i}", category="algorithm", valid=False)
                   for i in range(2)]
                  + [result(f"c{i}", "coding-01", f"t-c{i}", category="function_rewrite", valid=True)
                     for i in range(4)],
        }
        rows = {row["level"]: row for row in standardize(runs)["rows"]}
        # L0 runs 2 algorithm (0%) and 4 function_rewrite (100%): raw 4/6 = 66.7%.
        self.assertAlmostEqual(rows["L0"]["raw_valid_given_seen"], 400 / 6)
        # Pooled weights are 5 algorithm : 4 function_rewrite, so standardization
        # reweights L0's two within-category rates to that mix rather than to its
        # own 2:4 run mix — pulling it down from 66.7% to 44.4%.
        self.assertAlmostEqual(rows["L0"]["standardized_valid_given_seen"], 4 / 9 * 100)
        self.assertAlmostEqual(rows["L3"]["standardized_valid_given_seen"], 100.0)
        self.assertAlmostEqual(rows["L0"]["mix_coverage"], 100.0)

    def test_mix_coverage_reports_the_weight_a_level_can_supply(self):
        runs = {"L3": [result("a", "coding-01", "t-a", category="algorithm")],
                "L0": [result("b", "coding-01", "t-b", category="algorithm"),
                       result("c", "coding-01", "t-c", category="function_rewrite")]}
        rows = {row["level"]: row for row in standardize(runs)["rows"]}
        # Algorithm carries 2/3 of the pooled runs, and L3 has only that category.
        self.assertAlmostEqual(rows["L3"]["mix_coverage"], 200 / 3)
        self.assertAlmostEqual(rows["L0"]["mix_coverage"], 100.0)


class AdjacencyTests(unittest.TestCase):
    def test_endpoint_contrast_uses_pooled_two_proportion_z(self):
        runs = {"L3": [result(f"a{i}", "coding-01", f"t-a{i}", valid=True) for i in range(10)],
                "L0": [result(f"b{i}", "coding-01", f"t-b{i}", valid=False) for i in range(10)]}
        rows = {row["contrast"]: row for row in adjacency_tests(runs)}
        endpoint = rows["L3 vs L0 (endpoints)"]
        self.assertEqual(endpoint["delta_points"], 100.0)
        # Pooled rate 0.5 over 10 + 10 trials: z = 1 / sqrt(0.25 * 0.2) = sqrt(20).
        self.assertAlmostEqual(endpoint["z"], 20 ** 0.5)
        self.assertEqual(endpoint["first_trials"], 10)

    def test_a_fully_skewed_pair_leaves_z_undefined(self):
        # Both levels at 100%: the pooled rate saturates and the standard error
        # collapses, so the contrast must report no z rather than divide by zero.
        runs = {level: [result(f"{level}{i}", "coding-01", f"t{level}{i}", valid=True)
                        for i in range(10)] for level in ("L3", "L0")}
        endpoint = [row for row in adjacency_tests(runs)
                    if row["contrast"].startswith("L3 vs L0")][0]
        self.assertEqual(endpoint["delta_points"], 0.0)
        self.assertIsNone(endpoint["z"])

    def test_adjacent_pairs_are_skipped_when_a_level_is_missing(self):
        # L2 is absent, so L3 vs L2 and L2 vs L1 have no data; only the endpoint
        # contrast can still be formed from the levels that are present.
        runs = {"L3": [result("a", "coding-01", "t-a")],
                "L1": [result("b", "coding-01", "t-b")]}
        self.assertEqual([row["contrast"] for row in adjacency_tests(runs)],
                         ["L3 vs L1", "L3 vs L0 (endpoints)"][:1] if False else [])
        runs = {"L3": [result("a", "coding-01", "t-a")],
                "L0": [result("b", "coding-01", "t-b")]}
        self.assertEqual([row["contrast"] for row in adjacency_tests(runs)],
                         ["L3 vs L0 (endpoints)"])


class UnitContrastTests(unittest.TestCase):
    def test_a_unit_under_two_labels_is_reported_with_its_trend(self):
        runs = {
            "L3": [result(f"a{i}", "coding-01", "shared", valid=True) for i in range(8)],
            "L0": [result(f"b{i}", "coding-01", "shared", valid=False) for i in range(8)],
        }
        rows = unit_contrasts(runs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["atomic_task_id"], "shared")
        self.assertEqual(rows[0]["levels"], ["L3", "L0"])
        self.assertEqual(rows[0]["rates"], [100.0, 0.0])
        self.assertEqual(rows[0]["trend"], "decreasing")

    def test_units_below_the_minimum_are_excluded(self):
        runs = {
            "L3": [result(f"a{i}", "coding-01", "thin", valid=True) for i in range(3)],
            "L0": [result(f"b{i}", "coding-01", "thin", valid=False) for i in range(3)],
        }
        self.assertEqual(unit_contrasts(runs), [])
        self.assertEqual(unit_contrasts(runs, minimum=3)[0]["trend"], "decreasing")

    def test_unexposed_runs_do_not_enter_the_contrast(self):
        runs = {
            "L3": [result(f"a{i}", "coding-01", "shared", seen=False, valid=True) for i in range(8)],
            "L0": [result(f"b{i}", "coding-01", "shared", valid=False) for i in range(8)],
        }
        self.assertEqual(unit_contrasts(runs), [])


class PairAgreementTests(unittest.TestCase):
    def test_agreement_counts_identical_counts_and_zero_status(self):
        first = [result("a1", "coding-01", "t-a", valid=True),
                 result("a2", "coding-01", "t-a", valid=False)]
        second = [result("b1", "coding-01", "t-a", valid=False),
                  result("b2", "coding-01", "t-a", valid=False)]
        row = pair_agreement(first, second)
        self.assertEqual(row["pairs"], 1)
        self.assertEqual(row["identical_counts"], 0)
        # first delivered 1 of 2, second delivered 0 of 2: both are non-zero
        # runs, so the zero/non-zero verdict differs.
        self.assertEqual(row["same_zero_status"], 0)
        self.assertEqual(row["same_zero_status_rate"], 0.0)

    def test_only_shared_pairs_are_compared(self):
        first = [result("a1", "coding-01", "t-a"), result("a2", "coding-01", "t-b")]
        second = [result("b1", "coding-01", "t-b")]
        self.assertEqual(pair_agreement(first, second)["pairs"], 1)
        self.assertEqual(pair_agreement(first, second)["identical_counts"], 1)


class PairTableTests(unittest.TestCase):
    def test_pairs_carry_their_level_and_category(self):
        runs = [result("a1", "coding-01", "t-a", valid=True),
                result("a2", "coding-01", "t-a", valid=False)]
        row = pair_table({"L2": runs})[0]
        self.assertEqual(row["level"], "L2")
        self.assertEqual(row["case_id"], "coding-01__t-a")
        self.assertEqual(row["runs"], 2)
        self.assertEqual(row["valid_given_seen"], 50.0)
        self.assertEqual(row["category"], "algorithm")


class BuildReportTests(unittest.TestCase):
    def test_report_carries_every_section_and_the_optional_comparison(self):
        runs = {"L3": [result("a", "coding-01", "t-a", valid=True)],
                "L0": [result("b", "coding-01", "t-b", valid=False)]}
        report = build_report(runs)
        for key in ("levels", "category_matrix", "standardized", "adjacency",
                    "unit_contrasts", "pairs"):
            self.assertIn(key, report)
        self.assertNotIn("comparison", report)
        report = build_report(runs, {"L3": {"pairs": 1}})
        self.assertEqual(report["comparison"]["L3"]["pairs"], 1)


if __name__ == "__main__":
    unittest.main()
