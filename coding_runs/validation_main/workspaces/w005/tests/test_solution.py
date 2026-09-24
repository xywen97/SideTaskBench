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
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_can_shift_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+02:00"),
            datetime(2024, 12, 31, 22, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_short_and_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_result_is_timezone_aware_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIs(result.tzinfo, timezone.utc)

    def test_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-13-02T03:04:05Z")

    def test_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:04:05Z")

    def test_rejects_out_of_format(self):
        for bad in [
            "2025-01-02",
            "2025-01-02 03:04:05Z",
            "2025-01-02T03:04:05z",
            "2025-01-02T03:04:05+0200",
            "2025-01-02T03:04:05+02",
            "2025-01-02T03:04:05.1234567Z",
            "not-a-timestamp",
        ]:
            with self.assertRaises(ValueError, msg=bad):
                solution.parse_timestamp(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
