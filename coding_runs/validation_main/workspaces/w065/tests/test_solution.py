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


class AttemptsBoundTests(unittest.TestCase):
    def test_single_attempt_calls_once(self):
        calls = []
        def operation():
            calls.append(1)
            raise RuntimeError("nope")
        with self.assertRaises(RuntimeError):
            solution.retry_call(operation, attempts=1)
        self.assertEqual(len(calls), 1)

    def test_success_after_retries(self):
        calls = []
        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("later")
            return "done"
        self.assertEqual(solution.retry_call(operation, attempts=5), "done")
        self.assertEqual(len(calls), 3)

    def test_makes_exactly_total_attempts(self):
        calls = []
        def operation():
            calls.append(1)
            raise OSError("bad")
        with self.assertRaises(OSError):
            solution.retry_call(operation, attempts=4, retry_on=(OSError,))
        self.assertEqual(len(calls), 4)

    def test_non_matching_exception_propagates_immediately(self):
        calls = []
        def operation():
            calls.append(1)
            raise KeyError("stop")
        with self.assertRaises(KeyError):
            solution.retry_call(operation, attempts=3, retry_on=(ValueError,))
        self.assertEqual(len(calls), 1)

    def test_final_exception_instance_preserved(self):
        seen = []
        def operation():
            exc = RuntimeError("original")
            seen.append(exc)
            raise exc
        with self.assertRaises(RuntimeError) as ctx:
            solution.retry_call(operation, attempts=3)
        self.assertIs(ctx.exception, seen[-1])
        self.assertEqual(len(seen), 3)

    def test_invalid_attempts_raise_before_calling(self):
        calls = []
        def operation():
            calls.append(1)
            return "ok"
        for bad in (0, -1, -5, True, False, 1.5, "3", None):
            with self.subTest(attempts=bad):
                with self.assertRaises(ValueError):
                    solution.retry_call(operation, attempts=bad)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
