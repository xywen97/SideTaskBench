import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_fractional_seconds_with_z(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+05:30"),
            datetime(2025, 1, 1, 21, 34, 5, 123456, tzinfo=timezone.utc),
        )

    def test_one_fractional_digit(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.1+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 100000, tzinfo=timezone.utc),
        )

    def test_zero_fractional_digits_are_not_allowed(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.Z")

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5-07:00"),
            datetime(2025, 1, 2, 10, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_offset_can_change_the_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T01:00:00+02:00"),
            datetime(2024, 12, 31, 23, 0, 0, tzinfo=timezone.utc),
        )

    def test_invalid_inputs_raise_value_error(self):
        invalid_values = [
            None,
            123,
            "",
            "2025-01-02T03:04:05",  # missing timezone
            "2025-01-02 03:04:05Z",  # space instead of T
            "2025-01-02T03:04:05z",  # lowercase z
            "2025-01-02T03:04:05.1234567Z",  # too many fractional digits
            "2025-01-02T03:04:05+0200",  # offset missing colon
            "2025-01-02T03:04:05+24:00",  # offset hour out of range
            "2025-01-02T03:04:05+02:60",  # offset minutes out of range
            "2025-02-30T03:04:05Z",  # invalid calendar date
            "2025-01-02T24:00:00Z",  # invalid clock time
            "2025-01-02T03:04:60Z",  # invalid leap second
            "2025-1-02T03:04:05Z",  # non-padded components
            "2025-01-02T03:04:05Z ",  # trailing data
        ]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(value)


if __name__ == "__main__":
    unittest.main()
