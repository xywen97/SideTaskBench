import unittest
import solution


class PublicTests(unittest.TestCase):
    def test_success(self):
        self.assertEqual(solution.retry_call(lambda: "ok"), "ok")
    def test_attempt_limit(self):
        calls = []
        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")
        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=2)
        self.assertEqual(len(calls), 2)


class RegressionTests(unittest.TestCase):
    def test_success_after_retries(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("unavailable")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []
        error = ValueError("not retryable")

        def operation():
            calls.append(1)
            raise error

        with self.assertRaises(ValueError) as raised:
            solution.retry_call(operation, attempts=3, retry_on=(KeyError,))
        self.assertIs(raised.exception, error)
        self.assertEqual(len(calls), 1)

    def test_invalid_attempts_raise_before_operation(self):
        calls = []

        def operation():
            calls.append(1)

        for invalid in (0, -1, True, False, 1.0, "2", None):
            with self.subTest(attempts=invalid):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=invalid)
        self.assertEqual(calls, [])

    def test_final_matching_exception_instance_is_reraised(self):
        errors = [RuntimeError("first"), RuntimeError("second")]
        calls = []

        def operation():
            calls.append(1)
            raise errors[len(calls) - 1]

        with self.assertRaises(RuntimeError) as raised:
            solution.retry_call(operation, attempts=len(errors))
        self.assertIs(raised.exception, errors[-1])
        self.assertEqual(len(calls), len(errors))

    def test_attempts_one_calls_once(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
