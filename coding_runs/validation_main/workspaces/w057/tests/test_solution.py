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
    def test_default_is_three_total_attempts(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("down")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation)
        self.assertEqual(len(calls), 3)

    def test_succeeds_on_later_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")
            return "ok"

        self.assertEqual(solution.retry_call(operation, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []

        def operation():
            calls.append(1)
            raise KeyError("fatal")

        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=5, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_final_exception_instance_preserved(self):
        raised = RuntimeError("boom")

        def operation():
            raise raised

        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, raised)

    def test_invalid_attempts_raise_before_calling(self):
        calls = []

        def operation():
            calls.append(1)
            return "ok"

        for bad in (0, -1, True, False, 1.0, "2", None):
            with self.assertRaises(ValueError):
                solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])

    def test_attempts_of_one_calls_once(self):
        calls = []

        def operation():
            calls.append(1)
            raise RuntimeError("down")

        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
