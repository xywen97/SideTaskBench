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
    def test_retries_until_success_within_attempts(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("transient")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_default_attempts_is_three_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("nope")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_final_exception_instance_preserved(self):
        errors = []

        def operation():
            exc = RuntimeError("boom")
            errors.append(exc)
            raise exc

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, errors[-1])
        self.assertEqual(len(errors), 3)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("stop")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_single_attempt_does_not_retry(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("once")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)

    def test_invalid_attempts_raise_before_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, 1.5, "3", None, True, False):
            with self.subTest(attempts=bad):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
