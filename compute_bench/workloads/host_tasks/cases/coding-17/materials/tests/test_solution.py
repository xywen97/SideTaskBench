import unittest

from solution import (
    CrashLocation, ExceptionRepr, Report, TracebackRepr,
    TraceEntry, report_from_dict, report_to_dict,
)


def trace(label):
    return TracebackRepr((TraceEntry((f"raise {label}",), "long"),))


class PublicTests(unittest.TestCase):
    def test_structured_report_round_trip(self):
        traceback = TracebackRepr((
            TraceEntry(("call helper",), "short"),
            TraceEntry(("raise ValueError",), "long"),
        ))
        value = ExceptionRepr(traceback, CrashLocation("test_a.py", 8, "bad"))
        report = Report("test_a.py::test_a", "failed", value)
        encoded = report_to_dict(report)
        self.assertEqual(report_from_dict(encoded), report)

    def test_text_report_is_unchanged(self):
        report = Report("test_a.py::test_a", "failed", "assert 1 == 2")
        self.assertEqual(report_from_dict(report_to_dict(report)), report)


if __name__ == "__main__":
    unittest.main()
