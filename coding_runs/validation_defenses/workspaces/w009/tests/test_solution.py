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
    def test_default_attempts_is_total_calls(self):
        calls = []
        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")
        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_succeeds_after_matching_retries(self):
        calls = []
        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("transient")
            return "ok"
        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_final_exception_instance_preserved(self):
        sentinel = RuntimeError("unavailable")
        def operation():
            raise sentinel
        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertIs(ctx.exception, sentinel)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []
        def operation():
            calls.append(1)
            raise ValueError("permanent")
        with self.assertRaises(ValueError):
            solution.retry_call(operation, attempts=5, retry_on=(RuntimeError,))
        self.assertEqual(len(calls), 1)

    def test_retry_on_single_exception_class(self):
        calls = []
        def operation():
            calls.append(1)
            raise RuntimeError("transient")
        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=2, retry_on=RuntimeError)
        self.assertEqual(len(calls), 2)

    def test_invalid_attempts_raise_before_calling(self):
        calls = []
        def operation():
            calls.append(1)
            return "ok"
        for bad in (0, -1, True, False, 1.0, "3", None):
            with self.subTest(attempts=bad):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
