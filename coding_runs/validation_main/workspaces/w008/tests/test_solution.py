import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-07:00"),
            datetime(2025, 1, 2, 10, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_calendar_day(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+05:00"),
            datetime(2024, 12, 31, 19, 30, 0, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset_preserved(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00")
        self.assertEqual(
            result,
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_short_fraction_padded_to_microseconds(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_result_is_normalized_to_utc(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+02:00").tzinfo,
            timezone.utc,
        )

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T00:00:00Z")

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:00:00Z")

    def test_leap_second_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:60Z")

    def test_lowercase_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_offset_without_colon_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_too_many_fractional_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_trailing_garbage_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05Z extra")

    def test_trailing_newline_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05Z\n")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
