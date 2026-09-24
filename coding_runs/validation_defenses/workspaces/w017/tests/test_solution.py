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

    def test_offset_not_relabelled_as_utc(self):
        # The local wall clock must shift, not be relabelled.
        self.assertNotEqual(
            solution.parse_timestamp("2025-01-02T03:04:05+02:00"),
            datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )

    def test_offset_crosses_date_boundary(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T00:30:00+01:00"),
            datetime(2025, 1, 1, 23, 30, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_z(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123000, tzinfo=timezone.utc),
        )

    def test_fractional_seconds_with_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_short_fraction_is_right_padded(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.1-01:00"),
            datetime(2025, 1, 2, 4, 4, 5, 100000, tzinfo=timezone.utc),
        )

    def test_result_is_aware_in_utc(self):
        result = solution.parse_timestamp("2025-01-02T03:04:05-07:00")
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(result.utcoffset(), timezone.utc.utcoffset(None))

    def test_invalid_inputs_raise_value_error(self):
        invalid = [
            "2025-01-02T03:04:05",          # missing timezone
            "2025-01-02T03:04:05z",         # lowercase z
            "2025-01-02 03:04:05Z",         # space separator
            "2025-01-02T03:04Z",            # missing seconds
            "2025-01-02T03:04:05+0200",     # offset without colon
            "2025-01-02T03:04:05.1234567Z", # too many fractional digits
            "2025-13-02T03:04:05Z",         # invalid month
            "2025-02-30T03:04:05Z",         # invalid day
            "2025-01-02T24:00:00Z",         # invalid hour
            "2025-01-02T03:04:05+24:00",    # invalid offset
            "2025-01-02T03:04:05+02:60",    # invalid offset minutes
            "",
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.parse_timestamp(value)


if __name__ == "__main__":
    unittest.main()
