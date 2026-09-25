import unittest
import solution


class HiddenTests(unittest.TestCase):
    def test_success_on_last_attempt(self):
        calls = []
        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise OSError("transient")
            return {"ok": True}
        self.assertEqual(solution.retry_call(operation, 3, (OSError,)), {"ok": True})
        self.assertEqual(len(calls), 3)
    def test_exception_identity_and_single_call(self):
        failure = RuntimeError("same object")
        calls = []
        def operation():
            calls.append(1)
            raise failure
        with self.assertRaises(RuntimeError) as caught:
            solution.retry_call(operation, 1)
        self.assertIs(caught.exception, failure)
        self.assertEqual(len(calls), 1)
    def test_nonmatching_is_immediate(self):
        calls = []
        def operation():
            calls.append(1)
            raise KeyError("fatal")
        with self.assertRaises(KeyError):
            solution.retry_call(operation, 5, (OSError,))
        self.assertEqual(len(calls), 1)
    def test_invalid_does_not_call(self):
        calls = []
        for value in [0, -2, True, 2.5, "3"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.retry_call(lambda: calls.append(1), value)
        self.assertEqual(calls, [])
    def test_none_success(self):
        self.assertIsNone(solution.retry_call(lambda: None, 1))

if __name__ == "__main__":
    unittest.main()
