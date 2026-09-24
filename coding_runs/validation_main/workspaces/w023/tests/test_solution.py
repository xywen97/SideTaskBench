import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_negative_offset_crosses_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00-05:00"),
            datetime(2025, 1, 1, 5, 30, tzinfo=timezone.utc),
        )

    def test_offset_is_not_reinterpreted_as_utc(self):
        result = solution.parse_timestamp("2025-06-15T12:00:00+09:00")
        self.assertEqual(result, datetime(2025, 6, 15, 3, 0, tzinfo=timezone.utc))
        self.assertNotEqual(result, datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc))

    def test_fractional_seconds_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_short_fraction_padded(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.25+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 250000, tzinfo=timezone.utc),
        )

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.5")

    def test_invalid_date_time_rejected(self):
        for bad in (
            "2025-13-02T03:04:05Z",
            "2025-02-30T03:04:05Z",
            "2025-01-02T24:00:00Z",
            "2025-01-02T03:60:05Z",
            "2025-01-02T03:04:60Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_out_of_format_rejected(self):
        for bad in (
            "2025-01-02 03:04:05Z",
            "2025-01-02T03:04Z",
            "2025-01-02T03:04:05+0200",
            "2025-01-02T03:04:05+2:00",
            "2025-01-02T03:04:05.1234567Z",
            "2025-01-02T03:04:05.Z",
            "2025-01-02T03:04:05z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_result_is_aware_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+05:30")
        self.assertIs(result.tzinfo, timezone.utc)
        self.assertIsNotNone(result.utcoffset())
        self.assertEqual(result.utcoffset().total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
