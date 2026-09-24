import unittest

import solution


class AttemptsValidationTests(unittest.TestCase):
    def test_bool_is_rejected(self):
        for bad in (True, False):
            with self.assertRaises(ValueError):
                solution.retry_call(lambda: "ok", attempts=bad)

    def test_non_positive_is_rejected(self):
        for bad in (0, -1, -5):
            with self.assertRaises(ValueError):
                solution.retry_call(lambda: "ok", attempts=bad)

    def test_non_integer_is_rejected(self):
        for bad in (2.0, "3", None):
            with self.assertRaises(ValueError):
                solution.retry_call(lambda: "ok", attempts=bad)

    def test_validation_happens_before_calling_operation(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=0)
        self.assertEqual(calls, [])


class AttemptsBoundaryTests(unittest.TestCase):
    def test_attempts_one_makes_single_call(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=1), "ok")
        self.assertEqual(len(calls), 1)

    def test_retries_up_to_total_attempts(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_success_after_transient_failures(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("transient")
            return "done"

        self.assertEqual(solution.retry_call(operation, attempts=3), "done")
        self.assertEqual(len(calls), 3)


class ExceptionBehaviorTests(unittest.TestCase):
    def test_final_matching_exception_instance_is_preserved(self):
        error = RuntimeError("boom")

        def operation():
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertIs(ctx.exception, error)

    def test_non_matching_exception_propagates_immediately(self):
        error = KeyError("nope")
        calls = []

        def operation():
            calls.append(1)
            raise error

        with self.assertRaises(KeyError) as ctx:
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertIs(ctx.exception, error)
        self.assertEqual(len(calls), 1)

    def test_operation_arguments_are_used(self):
        class Custom(Exception):
            pass

        calls = []

        def operation():
            calls.append(1)
            raise Custom("x")

        with self.assertRaises(Custom):
            solution.retry_call(operation, attempts=2, retry_on=(Custom,))
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
