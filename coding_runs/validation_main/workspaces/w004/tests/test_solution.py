import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_result_is_normalized_to_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+05:30")
        self.assertIs(result.tzinfo, timezone.utc)

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:00"),
            datetime(2025, 1, 2, 8, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_can_change_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+01:00"),
            datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc),
        )

    def test_offset_is_not_reinterpreted_as_utc(self):
        # The wall-clock fields must not be kept while relabelling the zone.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(result.hour, 3)
        self.assertEqual(result.hour, 1)

    def test_fractional_seconds_with_z(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_short_fraction_is_right_padded(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fraction_preserved_across_offset_conversion(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123-02:30"),
            datetime(2025, 1, 2, 5, 34, 5, 123000, tzinfo=timezone.utc),
        )

    def test_zero_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_missing_timezone_with_fraction_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.123")

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T24:00:00Z")

    def test_leap_second_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:60Z")

    def test_too_many_fraction_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_basic_format_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("20250102T030405Z")

    def test_offset_without_colon_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_lowercase_designator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_out_of_range_offset_minutes_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+00:60")

    def test_out_of_range_offset_hours_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+24:00")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(datetime(2025, 1, 2, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
