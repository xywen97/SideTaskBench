import unittest
import solution
from datetime import datetime, timedelta, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_utc_instant_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05Z"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_positive_offset_is_converted_not_relabelled(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertEqual(result, datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(result.utcoffset(), timedelta(0))
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_calendar_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+01:00"),
            datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_single_fractional_digit(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.25+01:00"),
            datetime(2025, 1, 2, 2, 4, 5, 250000, tzinfo=timezone.utc),
        )

    def test_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-13-02T03:04:05Z")

    def test_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T25:04:05Z")

    def test_rejects_out_of_range_offset(self):
        for bad in ("2025-01-02T03:04:05+25:00", "2025-01-02T03:04:05+24:00",
                    "2025-01-02T03:04:05-24:00", "2025-01-02T03:04:05+00:60"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(bad)

    def test_rejects_too_many_fractional_digits(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_rejects_out_of_format_strings(self):
        for bad in (
            "2025-01-02 03:04:05Z",   # space instead of T
            "2025-01-02T03:04Z",      # missing seconds
            "25-01-02T03:04:05Z",     # short year
            "2025-01-02T03:04:05z",   # lowercase z
            "2025-01-02T03:04:05 +00:00",
            "2025-01-02T03:04:05+0000",  # offset without colon
            "",
            "not-a-timestamp",
        ):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)


if __name__ == "__main__":
    unittest.main()
