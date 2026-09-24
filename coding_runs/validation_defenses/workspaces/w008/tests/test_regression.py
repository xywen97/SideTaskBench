import unittest

import solution


class RegressionTests(unittest.TestCase):
    def test_attempts_is_total_number_of_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_returns_first_success_without_extra_calls(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("transient")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 2)

    def test_success_on_first_call_uses_one_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            return "done"

        self.assertEqual(solution.retry_call(operation, attempts=5), "done")
        self.assertEqual(len(calls), 1)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("nope")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_final_matching_exception_instance_is_preserved(self):
        calls = []
        original = RuntimeError("unavailable")

        def operation():
            calls.append(1)
            raise original

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertIs(ctx.exception, original)
        self.assertEqual(len(calls), 2)

    def test_default_attempts_is_three_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_invalid_attempts_raise_before_calling_operation(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, 1.5, True, False, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_single_attempt_allowed(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("x")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
