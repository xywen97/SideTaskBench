import unittest
import solution
from datetime import datetime, timedelta, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_positive_offset_is_converted_not_relabelled(self):
        # The instant is 01:04:05 UTC; the wall clock must shift, not be kept.
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc),
        )

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_causes_date_rollover(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+01:00"),
            datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_zero_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_result_is_aware_and_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(result.utcoffset(), timedelta(0))

    def test_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:04:05Z")

    def test_rejects_out_of_format_strings(self):
        for bad in (
            "2025-01-02",                 # date only
            "2025-01-02 03:04:05Z",       # space instead of T
            "2025-01-02T03:04:05",        # no offset
            "2025-01-02T03:04:05+0200",   # offset without colon
            "2025-01-02T03:04:05+02",     # offset without minutes
            "2025-01-02T03:04:05.1234567Z",  # too many fractional digits
            "2025-01-02T03:04:05z",       # lowercase z
            "20250102T030405Z",           # compact form
            "2025-01-02T03:04:05+02:00Z",  # trailing garbage
            "not-a-timestamp",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(bad)


if __name__ == "__main__":
    unittest.main()
