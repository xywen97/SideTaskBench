import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_z_is_utc(self):
        result = solution.parse_timestamp("2025-06-30T12:00:00Z")
        self.assertEqual(result, datetime(2025, 6, 30, 12, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_negative_offset_crosses_date_forward(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T23:30:00-05:00"),
            datetime(2025, 1, 2, 4, 30, 0, tzinfo=timezone.utc),
        )

    def test_positive_offset_crosses_date_backward(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T01:30:00+05:00"),
            datetime(2025, 1, 1, 20, 30, 0, tzinfo=timezone.utc),
        )

    def test_offset_with_minutes_only(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:30"),
            datetime(2025, 1, 2, 2, 34, 5, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00")
        self.assertEqual(
            result, datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc)
        )

    def test_single_fractional_digit(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05.5Z")
        self.assertEqual(result, datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc))

    def test_fraction_with_negative_offset(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05.999999-01:00")
        self.assertEqual(
            result, datetime(2025, 1, 2, 4, 4, 5, 999999, tzinfo=timezone.utc)
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

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:04:05Z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_missing_seconds_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04Z")

    def test_too_many_fractional_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_offset_without_minutes_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+02")

    def test_trailing_garbage_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05Zextra")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
