import unittest
from datetime import datetime, timedelta, timezone

import solution


class FractionalSecondsTests(unittest.TestCase):
    def test_one_fractional_digit(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.1Z"),
            datetime(2025, 1, 2, 3, 4, 5, 100000, tzinfo=timezone.utc),
        )

    def test_six_fractional_digits(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved_across_offsets(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.500-01:30"),
            datetime(2025, 1, 2, 4, 34, 5, 500000, tzinfo=timezone.utc),
        )


class OffsetNormalizationTests(unittest.TestCase):
    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:00"),
            datetime(2025, 1, 2, 8, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+05:30"),
            datetime(2024, 12, 31, 19, 0, 0, tzinfo=timezone.utc),
        )

    def test_offset_is_not_relabelled_as_utc(self):
        # A local offset must shift the instant, not merely swap the tzinfo.
        result = solution.parse_timestamp("2025-06-01T12:00:00+03:00")
        self.assertEqual(result, datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc))
        self.assertNotEqual(result.hour, 12)

    def test_result_is_utc_aware(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+01:00")
        self.assertEqual(result.utcoffset(), timedelta(0))
        self.assertIs(result.tzinfo, timezone.utc)


class RejectionTests(unittest.TestCase):
    def test_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_lowercase_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_too_many_fractional_digits(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T00:00:00Z")

    def test_invalid_time(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T24:00:00Z")

    def test_offset_out_of_range(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+24:00")

    def test_wrong_separator(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_date_only(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02")

    def test_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
