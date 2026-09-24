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
    def test_attempts_is_total_calls_not_retries(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        # First call succeeds, so exactly one call happens.
        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 1)

    def test_attempts_default_is_three_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("nope")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_eventually_succeeds_within_limit(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")
            return "done"

        self.assertEqual(solution.retry_call(operation, attempts=3), "done")
        self.assertEqual(len(calls), 3)

    def test_exhausted_attempts_uses_exactly_attempts_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("stop")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_final_matching_exception_instance_is_preserved(self):
        original = RuntimeError("the original")
        calls = []

        def operation():
            calls.append(1)
            raise original

        try:
            solution.retry_call(operation, attempts=3, retry_on=(RuntimeError,))
        except RuntimeError as caught:
            self.assertIs(caught, original)
        else:
            self.fail("expected RuntimeError")
        self.assertEqual(len(calls), 3)

    def test_attempts_zero_is_invalid_before_calling_operation(self):
        calls = []

        def operation():  # pragma: no cover - must never be called
            calls.append(1)
            return "ok"

        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=0)
        self.assertEqual(calls, [])

    def test_negative_attempts_is_invalid(self):
        with self.assertRaises(ValueError):
            solution.retry_call(lambda: "ok", attempts=-1)

    def test_bool_attempts_is_invalid(self):
        for value in (True, False):
            with self.assertRaises(ValueError):
                solution.retry_call(lambda: "ok", attempts=value)

    def test_non_integer_attempts_is_invalid(self):
        for value in (2.0, "2", None):
            with self.assertRaises(ValueError):
                solution.retry_call(lambda: "ok", attempts=value)


if __name__ == "__main__":
    unittest.main()
