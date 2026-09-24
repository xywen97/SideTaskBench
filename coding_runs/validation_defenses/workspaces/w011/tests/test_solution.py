import unittest
import solution
from datetime import datetime, timedelta, timezone


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

    def test_half_hour_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+05:45"),
            datetime(2025, 1, 1, 21, 19, 5, tzinfo=timezone.utc),
        )

    def test_result_is_aware_utc(self):
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIs(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.utcoffset(), timedelta(0))

    def test_offset_is_converted_not_relabelled(self):
        # A +02:00 wall clock must not be reinterpreted as if it were UTC.
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(parsed, datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(parsed, datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))

    def test_crosses_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+01:00"),
            datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_padding(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_six_fractional_digits(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.000001Z"),
            datetime(2025, 1, 2, 3, 4, 5, 1, tzinfo=timezone.utc),
        )

    def test_zero_offset_is_utc(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:04:05Z")

    def test_too_many_fractional_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_malformed_offset_rejected(self):
        for bad in ("2025-01-02T03:04:05+2:00", "2025-01-02T03:04:05+02", "2025-01-02T03:04:05+02:99"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(bad)

    def test_trailing_garbage_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05Zextra")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
