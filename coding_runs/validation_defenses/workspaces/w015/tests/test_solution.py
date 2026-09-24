import unittest
import solution
from datetime import datetime, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class RegressionTests(unittest.TestCase):
    def test_negative_offset_normalized(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_crossing_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+05:30"),
            datetime(2024, 12, 31, 19, 0, 0, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved_with_z(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_preserved_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_one_to_six_fractional_digits(self):
        for digits, micro in (("1", 100000), ("12", 120000), ("123456", 123456)):
            with self.subTest(digits=digits):
                result = solution.parse_timestamp("2025-01-02T03:04:05.%sZ" % digits)
                self.assertEqual(result.microsecond, micro)

    def test_result_is_timezone_aware_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertIs(result.tzinfo, timezone.utc)

    def test_reject_missing_timezone(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_reject_invalid_date(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_reject_invalid_time(self):
        for value in ("2025-01-02T25:04:05Z", "2025-01-02T03:60:05Z", "2025-01-02T03:04:60Z"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_out_of_format(self):
        for value in (
            "2025-01-02 03:04:05Z",      # space separator
            "2025-01-02T03:04Z",         # missing seconds
            "2025-01-02T03:04:05+0200",  # offset without colon
            "2025-01-02T03:04:05.1234567Z",  # too many fractional digits
            "2025-01-02T03:04:05Zx",
            "2025-1-02T03:04:05Z",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.parse_timestamp(value)

    def test_reject_out_of_range_offset(self):
        for value in ("2025-01-02T03:04:05+24:00", "2025-01-02T03:04:05+02:60"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.parse_timestamp(value)


if __name__ == "__main__":
    unittest.main()
