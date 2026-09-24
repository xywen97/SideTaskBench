import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def assert_utc(self, value, expected):
        result = solution.parse_timestamp(value)
        self.assertEqual(result, expected)
        self.assertIs(result.tzinfo, timezone.utc)

    def test_zero_offset_is_utc(self):
        self.assert_utc(
            "2025-01-02T03:04:05+00:00",
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_negative_offset_moves_forward(self):
        self.assert_utc(
            "2025-01-02T03:04:05-05:00",
            datetime(2025, 1, 2, 8, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_rolls_over_calendar_date(self):
        # 23:30 at +05:00 is 18:30 UTC the same day; 02:00 at +05:00 is the
        # previous day in UTC.
        self.assert_utc(
            "2025-01-02T02:00:00+05:00",
            datetime(2025, 1, 1, 21, 0, 0, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved_z(self):
        self.assert_utc(
            "2025-01-02T03:04:05.123456Z",
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_padded(self):
        # ".5" means 500000 microseconds, not 5.
        self.assert_utc(
            "2025-01-02T03:04:05.5Z",
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset_conversion(self):
        self.assert_utc(
            "2025-01-02T03:04:05.000123+02:00",
            datetime(2025, 1, 2, 1, 4, 5, 123, tzinfo=timezone.utc),
        )

    def test_all_fractional_lengths(self):
        for digits, micros in (
            ("1", 100000),
            ("12", 120000),
            ("123", 123000),
            ("1234", 123400),
            ("12345", 123450),
            ("123456", 123456),
        ):
            self.assert_utc(
                "2025-01-02T03:04:05.{}Z".format(digits),
                datetime(2025, 1, 2, 3, 4, 5, micros, tzinfo=timezone.utc),
            )

    def test_mixed_offset_normalization(self):
        # Two representations of the same instant must compare equal.
        a = solution.parse_timestamp("2025-01-02T03:04:05Z")
        b = solution.parse_timestamp("2025-01-02T05:04:05+02:00")
        self.assertEqual(a, b)

    def test_local_offset_not_reinterpreted(self):
        # +02:00 must shift the wall clock back by two hours, not be relabelled.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertEqual(result.hour, 1)
        self.assertNotEqual(result.replace(tzinfo=None), datetime(2025, 1, 2, 3, 4, 5))

    def test_reject_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_reject_fractional_without_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.123")

    def test_reject_trailing_z_suffixes(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05ZZ")

    def test_reject_non_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(datetime(2025, 1, 2, 3, 4, 5))

    def test_reject_leading_or_trailing_whitespace(self):
        for value in (
            " 2025-01-02T03:04:05Z",
            "2025-01-02T03:04:05Z ",
            "2025-01-02T03:04:05Z\n",
            "2025-01-02T03:04:05Z\t",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_lowercase_separators(self):
        for value in ("2025-01-02t03:04:05Z", "2025-01-02T03:04:05z"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_missing_seconds(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04Z")

    def test_reject_compact_military_offset(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_reject_too_many_fractional_digits(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_reject_invalid_calendar_dates(self):
        for value in (
            "2025-13-01T03:04:05Z",
            "2025-02-30T03:04:05Z",
            "2025-00-10T03:04:05Z",
            "2025-01-32T03:04:05Z",
            "0000-01-01T03:04:05Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_invalid_times(self):
        for value in (
            "2025-01-02T24:00:00Z",
            "2025-01-02T03:60:00Z",
            "2025-01-02T03:04:60Z",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_invalid_offset(self):
        for value in (
            "2025-01-02T03:04:05+24:00",
            "2025-01-02T03:04:05+02:60",
            "2025-01-02T03:04:05+2:00",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_empty_string(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("")

    def test_naive_not_treated_as_utc(self):
        # Guard against the historical replace(tzinfo=utc) bug: a local time
        # must never silently equal the same wall clock in UTC.
        naive = "2025-01-02T03:04:05-05:00"
        self.assertNotEqual(
            solution.parse_timestamp(naive),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
