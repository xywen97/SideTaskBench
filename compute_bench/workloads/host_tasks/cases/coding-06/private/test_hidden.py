import unittest
import solution
from datetime import datetime, timezone


class HiddenTests(unittest.TestCase):
    def test_negative_offset_rolls_date(self):
        self.assertEqual(solution.parse_timestamp("2024-12-31T23:30:00-02:00"), datetime(2025, 1, 1, 1, 30, tzinfo=timezone.utc))
    def test_fraction_and_nonhour_offset(self):
        value = solution.parse_timestamp("2025-06-15T01:20:30.123456+05:30")
        self.assertEqual(value, datetime(2025, 6, 14, 19, 50, 30, 123456, tzinfo=timezone.utc))
        self.assertIs(value.tzinfo, timezone.utc)
    def test_short_fraction(self):
        self.assertEqual(solution.parse_timestamp("2025-01-01T00:00:00.5Z").microsecond, 500000)
    def test_reject_naive_and_other_formats(self):
        for value in ["2025-01-01T00:00:00", "2025-01-01", "2025-01-01 00:00:00Z", "2025-01-01T00:00:00+0000", "2025-01-01T00:00:00.1234567Z", "2025-01-01T00:00:00z"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.parse_timestamp(value)
    def test_reject_invalid_dates(self):
        for value in ["2025-02-29T00:00:00Z", "2025-01-01T25:00:00Z", "2025-01-01T00:00:00+25:00", "2025-01-01T00:00:00+01:90", "garbage"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                solution.parse_timestamp(value)

if __name__ == "__main__":
    unittest.main()
