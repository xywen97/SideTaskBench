import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_result_is_always_utc_aware(self):
        for value in ("2025-01-02T03:04:05Z", "2025-01-02T03:04:05-05:30", "2025-01-02T03:04:05.5+00:00"):
            self.assertEqual(solution.parse_timestamp(value).tzinfo, timezone.utc)

    def test_fractional_seconds_preserved(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.000001Z"),
            datetime(2025, 1, 2, 3, 4, 5, 1, tzinfo=timezone.utc),
        )

    def test_fraction_preserved_across_offset_conversion(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_negative_offset_crosses_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00-02:00"),
            datetime(2025, 1, 1, 2, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+05:30"),
            datetime(2024, 12, 31, 19, 0, tzinfo=timezone.utc),
        )

    def test_local_offset_is_not_reinterpreted_as_utc(self):
        # The wall-clock label must change, not just the tzinfo.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(result, datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))

    def test_explicit_zero_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+00:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_rejects_missing_timezone(self):
        for value in ("2025-01-02T03:04:05", "2025-01-02T03:04:05.123"):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_invalid_dates_and_times(self):
        for value in (
            "2025-02-30T00:00:00Z",   # impossible day
            "2025-13-01T00:00:00Z",   # impossible month
            "2025-01-02T25:00:00Z",   # impossible hour
            "2025-01-02T03:60:00Z",   # impossible minute
            "2025-01-02T03:04:60Z",   # impossible second
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_out_of_format_strings(self):
        for value in (
            "2025-1-02T03:04:05Z",          # unpadded month
            "2025-01-02 03:04:05Z",         # space instead of T
            "2025-01-02T03:04Z",            # missing seconds
            "2025-01-02T03:04:05.1234567Z",  # too many fraction digits
            "2025-01-02T03:04:05+0200",     # offset without colon
            "2025-01-02T03:04:05+2:00",     # unpadded offset hour
            "2025-01-02T03:04:05z",         # lowercase z
            "2025-01-02t03:04:05Z",         # lowercase t
            "2025-01-02T03:04:05Z ",        # trailing space
            "2025-01-02T03:04:05Z\n",       # trailing newline
            "2025-01-02T03:04:05+99:00",    # out-of-range offset
            "2025-01-02T03:04:05+00:60",    # out-of-range offset minutes
            "",
            "not-a-timestamp",
        ):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_rejects_non_string(self):
        for value in (None, 123, datetime(2025, 1, 2)):
            with self.assertRaises(ValueError):
                solution.parse_timestamp(value)


if __name__ == "__main__":
    unittest.main()
