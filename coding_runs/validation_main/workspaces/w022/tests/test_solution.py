import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_negative_offset(self):
        # 03:04:05-05:30 is 08:34:05 UTC.
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T23:30:00+02:00"),
            datetime(2025, 1, 1, 21, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00-02:00"),
            datetime(2025, 1, 1, 2, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved(self):
        expected = datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc)
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00"), expected)
        self.assertEqual(solution.parse_timestamp("2025-01-02T01:04:05.123456Z"), expected)

    def test_offset_time_is_not_reinterpreted_as_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(result, datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(result.utcoffset().total_seconds(), 0)

    def test_result_is_utc_aware(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05Z")
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_rejects_missing_timezone(self):
        for bad in ("2025-01-02T03:04:05", "2025-01-02T03:04:05.5"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_rejects_out_of_format_strings(self):
        bad_values = [
            "",
            "2025-01-02",
            "2025-01-02 03:04:05Z",
            "2025-01-02T03:04Z",
            "2025-01-02T03:04:05+02",
            "2025-01-02T03:04:05+0200",
            "2025-01-02T03:04:05+02:00 extra",
            "2025-01-02T03:04:05z",
            "2025-01-02T03:04:05.1234567Z",
            "2025-01-02T03:04:05+24:00",
            "2025-01-02T03:04:05+02:60",
        ]
        for bad in bad_values:
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_rejects_invalid_dates_and_times(self):
        for bad in (
            "2025-13-02T03:04:05Z",
            "2025-02-30T03:04:05Z",
            "2025-01-02T25:04:05Z",
            "2025-01-02T03:60:05Z",
            "2025-01-02T03:04:60Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_rejects_non_string(self):
        for bad in (None, 123, b"2025-01-02T03:04:05Z"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)


if __name__ == "__main__":
    unittest.main()
