import unittest
import solution
from datetime import datetime, timedelta, timezone


class PublicTests(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05Z"), datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    def test_positive_offset(self):
        self.assertEqual(solution.parse_timestamp("2025-01-02T03:04:05+02:00"), datetime(2025, 1, 2, 1, 4, 5, tzinfo=timezone.utc))


class OffsetNormalizationTests(unittest.TestCase):
    def test_negative_offset_shifts_wall_clock(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05-05:30"),
            datetime(2025, 1, 2, 8, 34, 5, tzinfo=timezone.utc),
        )

    def test_offset_is_not_reinterpreted_as_utc(self):
        # The wall clock must change; relabeling would keep 03:04:05.
        result = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertNotEqual(result.replace(tzinfo=None), datetime(2025, 1, 2, 3, 4, 5))

    def test_conversion_can_change_the_date(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-01T00:30:00+02:00"),
            datetime(2024, 12, 31, 22, 30, tzinfo=timezone.utc),
        )

    def test_instant_is_preserved(self):
        original = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=5, minutes=45)))
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+05:45")
        self.assertEqual(parsed, original)
        self.assertEqual(parsed.astimezone(timezone(timedelta(hours=5, minutes=45))), original)

    def test_result_is_utc_aware(self):
        parsed = solution.parse_timestamp("2025-01-02T03:04:05+02:00")
        self.assertEqual(parsed.tzinfo, timezone.utc)


class FractionalSecondTests(unittest.TestCase):
    def test_fraction_preserved_with_z(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.123456Z"),
            datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
        )

    def test_fraction_padded_to_microseconds(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.5Z"),
            datetime(2025, 1, 2, 3, 4, 5, 500000, tzinfo=timezone.utc),
        )

    def test_fraction_preserved_across_offset(self):
        self.assertEqual(
            solution.parse_timestamp("2025-01-02T03:04:05.000001+02:00"),
            datetime(2025, 1, 2, 1, 4, 5, 1, tzinfo=timezone.utc),
        )

    def test_one_to_six_digits_accepted(self):
        for digits in range(1, 7):
            fraction = "0" * (digits - 1) + "1"
            text = "2025-01-02T03:04:05." + fraction + "Z"
            expected_micro = int(fraction.ljust(6, "0"))
            self.assertEqual(
                solution.parse_timestamp(text),
                datetime(2025, 1, 2, 3, 4, 5, expected_micro, tzinfo=timezone.utc),
                msg=text,
            )


class RejectionTests(unittest.TestCase):
    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05")

    def test_missing_timezone_with_fraction_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.123")

    def test_invalid_month_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-13-02T03:04:05Z")

    def test_invalid_day_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-02-30T03:04:05Z")

    def test_invalid_hour_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T24:04:05Z")

    def test_invalid_minute_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:60:05Z")

    def test_invalid_second_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:60Z")

    def test_invalid_offset_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+24:00")

    def test_seven_fraction_digits_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05.1234567Z")

    def test_space_separator_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02 03:04:05Z")

    def test_offset_without_colon_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+0200")

    def test_lowercase_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05z")

    def test_double_z_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05ZZ")

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("")

    def test_garbage_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("not-a-timestamp")
    def test_out_of_range_instant_rejected(self):
        # Valid text, but the converted instant exceeds datetime.max.
        with self.assertRaises(ValueError):
            solution.parse_timestamp("9999-12-31T23:59:59-05:00")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp(None)

    def test_offset_minutes_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            solution.parse_timestamp("2025-01-02T03:04:05+02:60")


if __name__ == "__main__":
    unittest.main()
