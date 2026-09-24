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
    def test_attempts_counts_total_calls_not_retries(self):
        calls = []

        def operation():
            calls.append(1)
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=3)

        self.assertEqual(len(calls), 3)

    def test_succeeds_on_later_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")
            return "done"

        self.assertEqual(solution.retry_call(operation, attempts=3), "done")
        self.assertEqual(len(calls), 3)

    def test_single_attempt_calls_once(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)

        self.assertEqual(len(calls), 1)

    def test_invalid_attempts_raise_before_calling_operation(self):
        called = []

        def operation():
            called.append(1)
            return "ok"

        for invalid in (0, -1, -10, 1.5, "3", None, True, False):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=invalid)
        self.assertEqual(called, [])

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("nope")

        with self.assertRaises(KeyError) as ctx:
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))

        self.assertEqual(len(calls), 1)
        self.assertIsInstance(ctx.exception, KeyError)

    def test_matching_tuple_retries(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("first")
            if len(calls) == 2:
                raise KeyError("second")
            return "third"

        result = solution.retry_call(operation, attempts=3, retry_on=(KeyError, RuntimeError))
        self.assertEqual(result, "third")
        self.assertEqual(len(calls), 3)

    def test_final_exception_instance_is_preserved(self):
        created = []

        def operation():
            exc = RuntimeError("original")
            created.append(exc)
            raise exc

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)

        self.assertIs(ctx.exception, created[-1])
        self.assertEqual(len(created), 3)


if __name__ == "__main__":
    unittest.main()
