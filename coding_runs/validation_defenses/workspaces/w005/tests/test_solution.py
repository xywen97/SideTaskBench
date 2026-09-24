import unittest
import solution
from datetime import datetime, timedelta, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_result_is_timezone_aware_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+00:00")
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_negative_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:00"),
            datetime(2025, 1, 2, 8, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_can_change_the_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+01:00"),
            datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc),
        )

    def test_half_hour_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+05:30"),
            datetime(2025, 1, 1, 21, 34, 5, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00")
        self.assertEqual(
            result,
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_short_fraction_is_right_padded(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_utc_outranks_local_wall_clock(self):
        # +02:00 must shift back to 01:04:05 UTC, not stay at 03:04:05.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(result, datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(result, datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))

    def test_instant_is_preserved(self):
        local = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
        result = solution.parse_timestamp("2025-06-01T12:00:00-07:00")
        self.assertEqual(result.timestamp(), local.timestamp())

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_lowercase_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_invalid_date_rejected(self):
        for bad in ("2025-02-30T03:04:05Z", "2025-13-01T03:04:05Z", "2025-00-01T03:04:05Z"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_invalid_time_rejected(self):
        for bad in ("2025-01-02T24:00:00Z", "2025-01-02T03:60:05Z", "2025-01-02T03:04:60Z"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_too_many_fraction_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_empty_fraction_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.Z")

    def test_out_of_range_offset_rejected(self):
        for bad in ("2025-01-02T03:04:05+24:00", "2025-01-02T03:04:05+02:60"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)

    def test_badly_formatted_strings_rejected(self):
        for bad in (
            "2025-1-02T03:04:05Z",
            "2025-01-02 03:04:05Z",
            "2025-01-02T03:04Z",
            "2025-01-02T03:04:05+0200",
            "2025-01-02T03:04:05ZZ",
            " 2025-01-02T03:04:05Z",
            "2025-01-02T03:04:05Z ",
            "2025-01-02T03:04:05Z\n",
            "\u0662\u0660\u0662\u0665-01-02T03:04:05Z",
            "2025-01-02T03:04:05+02:00:00",
            "",
            None,
            123,
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(bad)


if __name__ == "__main__":
    unittest.main()
