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

    def test_zero_offset_matches_utc(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_are_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.000001Z"),
            datetime(2025, 1, 2, 3, 4, 5, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_convert_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.250+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 250000, tzinfo=timezone.utc),
        )

    def test_result_is_timezone_aware_utc(self):
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)

    def test_missing_timezone_is_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_invalid_calendar_date_and_time_are_rejected(self):
        for value in (
            "2025-13-02T03:04:05Z",
            "2025-02-30T03:04:05Z",
            "2025-01-02T24:00:00Z",
            "2025-01-02T03:60:00Z",
            "2025-01-02T03:04:60Z",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(value)

    def test_strings_outside_format_are_rejected(self):
        for value in (
            "2025-01-02 03:04:05Z",       # space instead of T
            "2025-01-02T03:04Z",          # seconds missing
            "2025-01-02T03:04:05.Z",      # fraction separator without digits
            "2025-01-02T03:04:05.1234567Z",  # more than six fraction digits
            "2025-01-02T03:04:05z",       # lowercase designator
            "2025-01-02T03:04:05+0200",   # offset without colon
            "2025-01-02T03:04:05+99:00",  # out-of-range offset
            "2025-1-02T03:04:05Z",        # unpadded component
            "2025-01-02T03:04:05Z\n",     # trailing content
            "",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(value)


if __name__ == "__main__":
    unittest.main()
