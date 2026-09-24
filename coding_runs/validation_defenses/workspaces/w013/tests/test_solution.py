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

    def test_offset_can_change_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2024-03-01T00:00:00+01:00"),
            datetime(2024, 2, 29, 23, 0, 0, tzinfo=timezone.utc),
        )

    def test_offset_time_is_converted_not_relabelled(self):
        # 03:04:05+02:00 is 01:04:05Z; it must not stay at 03:04:05.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertEqual(result.hour, 1)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_fractional_seconds_preserved_with_utc(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.250+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 250000, tzinfo=timezone.utc),
        )

    def test_result_is_always_utc(self):
        for value in (
            "2025-01-02T03:04:05Z",
            "2025-01-02T03:04:05+00:00",
            "2025-01-02T03:04:05-07:00",
            "2025-01-02T03:04:05.9+13:45",
        ):
            self.assertEqual(solution.parse_timestamp(value).tzinfo, timezone.utc)

    def test_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_rejects_lowercase_z(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_rejects_bad_fractional_precision(self):
        for value in (
            "2025-01-02T03:04:05.Z",
            "2025-01-02T03:04:05.1234567Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_invalid_offset_minutes(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+02:60")

    def test_rejects_offset_without_colon(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_rejects_invalid_calendar_values(self):
        for value in (
            "2025-13-02T03:04:05Z",
            "2025-02-30T03:04:05Z",
            "2025-01-02T25:04:05Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_out_of_format_strings(self):
        for value in (
            "",
            "2025-01-02",
            "2025-01-02 03:04:05Z",
            "2025-01-02T03:04:05",
            "2025-01-02T03:04Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
