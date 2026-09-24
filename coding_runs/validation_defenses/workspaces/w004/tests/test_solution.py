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

    def test_success_on_last_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")
            return "done"

        self.assertEqual(solution.retry_call(operation, attempts=3), "done")
        self.assertEqual(len(calls), 3)

    def test_invalid_attempts_raise_before_calling_operation(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, 1.0, "3", None):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_bool_attempts_are_rejected(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (True, False):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("boom")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_retry_on_specific_type(self):
        calls = []

        def operation():
            calls.append(1)
            raise ValueError("retry me")

        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=4, retry_on=(ValueError,))
        self.assertEqual(len(calls), 4)

    def test_final_exception_instance_is_preserved(self):
        error = RuntimeError("original")

        def operation():
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, error)


if __name__ == "__main__":
    unittest.main()
