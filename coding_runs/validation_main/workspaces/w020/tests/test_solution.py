import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_fractional_seconds_utc(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_padded(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.000001+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 1, tzinfo=timezone.utc),
        )

    def test_negative_offset_converts(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_can_change_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00-02:00"),
            datetime(2025, 1, 1, 2, 30, 0, tzinfo=timezone.utc),
        )

    def test_offset_not_reinterpreted_as_utc(self):
        # The instant must shift, not just the tzinfo label.
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(parsed.hour, 3)
        self.assertEqual(parsed.hour, 1)

    def test_zero_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_lowercase_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_invalid_month_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-13-01T03:04:05Z")

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T24:00:00Z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_offset_without_colon_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_too_many_fractional_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_trailing_dot_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.Z")

    def test_out_of_range_offset_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+24:00")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
