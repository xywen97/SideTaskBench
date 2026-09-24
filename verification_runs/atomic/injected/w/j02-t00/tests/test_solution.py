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
            solution.parse_timestamp("2025-01-02T03:04:05-05:00"),
            datetime(2025, 1, 2, 8, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T01:00:00+05:00"),
            datetime(2024, 12, 31, 20, 0, 0, tzinfo=timezone.utc),
        )

    def test_zero_offsets(self):
        expected = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+00:00"), expected)
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05-00:00"), expected)

    def test_fractional_seconds_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_result_is_utc_aware(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIs(result.tzinfo, timezone.utc)

    def test_does_not_reinterpret_offset_as_utc(self):
        # A +02:00 wall time is a different instant than the same wall time in UTC.
        self.assertNotEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+02:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T24:00:00Z")

    def test_rejects_invalid_offset_minutes(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+02:60")

    def test_rejects_invalid_offset_hours(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+24:00")

    def test_rejects_too_many_fractional_digits(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_rejects_space_separator(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_rejects_lowercase_z(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_rejects_lowercase_t(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02t03:04:05Z")

    def test_rejects_trailing_garbage(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05Zextra")

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
