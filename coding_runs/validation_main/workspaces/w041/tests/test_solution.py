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
    def test_total_attempts_counts_initial_call(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=3)
        self.assertEqual(len(calls), 3)

    def test_single_attempt_makes_one_call(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("unavailable")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)

    def test_succeeds_after_retries(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_invalid_attempts_raise_value_error_without_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, -5, True, False, 1.0, "2", None):
            with self.subTest(attempts=bad):
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

    def test_final_exception_instance_preserved(self):
        error = RuntimeError("original")

        def operation():
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, error)

    def test_retry_on_tuple_selects_matching(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("first")
            return "ok"

        self.assertEqual(
            solution.retry_call(operation, attempts=3, retry_on=(ValueError, KeyError)),
            "ok",
        )
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
