import unittest

import solution


class RetryCallRegressionTests(unittest.TestCase):
    def test_success_returns_first_result(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        self.assertEqual(solution.retry_call(operation), "ok")
        self.assertEqual(len(calls), 1)

    def test_attempts_is_total_number_of_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_default_attempts_is_three_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_succeeds_on_later_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("transient")
            return "recovered"

        self.assertEqual(solution.retry_call(operation, attempts=3), "recovered")
        self.assertEqual(len(calls), 2)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("not retryable")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_final_exception_instance_is_preserved(self):
        errors = []

        def operation():
            error = RuntimeError("boom-%d" % len(errors))
            errors.append(error)
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertIs(ctx.exception, errors[-1])

    def test_invalid_attempts_raise_before_calling_operation(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, -5, True, False, 1.5, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_bool_is_rejected_even_though_int_subclass(self):
        with self.assertRaises(ValueError):
            solution.retry_call(lambda: "ok", attempts=True)

    def test_attempts_of_one_calls_once(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
