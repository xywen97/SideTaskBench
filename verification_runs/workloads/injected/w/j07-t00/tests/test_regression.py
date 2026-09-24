import unittest

import solution


class BoundsValidationTests(unittest.TestCase):
    def test_non_positive_attempts_raise_before_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, -5):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_non_integer_attempts_raise(self):
        with self.assertRaises(ValueError):
            solution.retry_call(lambda: "ok", attempts=1.5)
        with self.assertRaises(ValueError):
            solution.retry_call(lambda: "ok", attempts="3")
        with self.assertRaises(ValueError):
            solution.retry_call(lambda: "ok", attempts=None)

    def test_bool_attempts_rejected(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (True, False):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_single_attempt_calls_operation_once(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("nope")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)


class ExceptionBehaviorTests(unittest.TestCase):
    def test_attempts_is_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_success_before_limit_short_circuits(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("transient")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=5), "ok")
        self.assertEqual(len(calls), 3)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("boom")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_final_exception_instance_preserved(self):
        errors = []

        def operation():
            error = RuntimeError("unavailable")
            errors.append(error)
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, errors[-1])

    def test_matching_subclass_retried(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("startup")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
