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
    def test_default_attempts_means_total_calls(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("nope")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_success_stops_calling(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("nope")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=5), "ok")
        self.assertEqual(len(calls), 3)

    def test_non_matching_exception_propagates_without_retry(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("boom")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_final_matching_exception_instance_is_preserved(self):
        error = RuntimeError("original")

        def operation():
            raise error

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=2)
        self.assertIs(ctx.exception, error)

    def test_attempts_must_be_positive_int(self):
        for bad in (0, -1, 1.0, "3", None, True, False):
            calls = []

            def operation():
                calls.append(1)
                return "ok"

            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
            self.assertEqual(calls, [], "operation called for %r" % (bad,))


if __name__ == "__main__":
    unittest.main()
