import unittest

import solution


class RetryCallRegressionTests(unittest.TestCase):
    def test_returns_first_successful_result(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        self.assertEqual(solution.retry_call(operation), "ok")
        self.assertEqual(len(calls), 1)

    def test_attempts_is_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_attempts_one_calls_once(self):
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
            raise KeyError("nope")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_final_exception_instance_preserved(self):
        seen = []

        def operation():
            exc = RuntimeError("unique")
            seen.append(exc)
            raise exc

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertEqual(len(seen), 2)
        self.assertIs(ctx.exception, seen[-1])

    def test_invalid_attempts_raise_before_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, 1.5, "3", None, True, False):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
