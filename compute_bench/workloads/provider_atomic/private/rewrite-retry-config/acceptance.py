import builtins
import copy
import unittest
import solution

class Acceptance(unittest.TestCase):
    def test_codes_are_copied_without_aliasing(self):
        for codes in ([], [503, 429, 503]):
            with self.subTest(codes=codes):
                config = {"attempts": 2, "delay_ms": 125, "codes": codes}
                before = copy.deepcopy(config)
                result = solution.adapt_retry(config)
                self.assertEqual(result, {"max_attempts": 2, "base_delay_seconds": 0.125,
                                          "retry_codes": codes})
                self.assertIsInstance(result["retry_codes"], list)
                self.assertIsNot(result["retry_codes"], codes)
                result["retry_codes"].append(500)
                self.assertEqual(config, before)

    def test_private_cases(self):
        cases = [{'args': [{'attempts': 3, 'delay_ms': 250, 'codes': [429, 503]}], 'expected': {'max_attempts': 3, 'base_delay_seconds': 0.25, 'retry_codes': [429, 503]}, 'no_mutation': True}, {'args': [{'attempts': 1, 'delay_ms': 0, 'codes': [500, 500]}], 'expected': {'max_attempts': 1, 'base_delay_seconds': 0, 'retry_codes': [500, 500]}}]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                args = copy.deepcopy(case.get("args", []))
                kwargs = copy.deepcopy(case.get("kwargs", {}))
                before = copy.deepcopy((args, kwargs))
                if "raises" in case:
                    with self.assertRaises(getattr(builtins, case["raises"])):
                        solution.adapt_retry(*args, **kwargs)
                else:
                    self.assertEqual(solution.adapt_retry(*args, **kwargs), case["expected"])
                if case.get("no_mutation"):
                    self.assertEqual((args, kwargs), before)
