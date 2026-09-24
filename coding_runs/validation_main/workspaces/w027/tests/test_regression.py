import unittest

import solution


class RetryCallRegressionTests(unittest.TestCase):
    def test_attempts_is_total_number_of_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_success_before_attempt_limit(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("try again")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=5), "ok")
        self.assertEqual(len(calls), 3)

    def test_retry_on_filters_exception_types(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("fatal")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_final_matching_exception_instance_preserved(self):
        calls = []
        errors = []

        def operation():
            calls.append(1)
            error = RuntimeError("failure %d" % len(calls))
            errors.append(error)
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, errors[-1])
        self.assertEqual(len(calls), 3)

    def test_invalid_attempts_raise_value_error_before_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for invalid in (0, -1, True, False, 2.0, "3", None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=invalid)
        self.assertEqual(calls, [])

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("fatal")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=4, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
