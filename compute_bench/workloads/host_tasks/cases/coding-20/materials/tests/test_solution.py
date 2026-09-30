import unittest

from solution import read_rst_table, write_rst_table


class PublicTests(unittest.TestCase):
    def test_existing_single_header_behavior(self):
        columns = [
            {"name": "left", "values": ["a", "b"]},
            {"name": "right", "values": ["1", "2"]},
        ]
        self.assertEqual(read_rst_table(write_rst_table(columns)), columns)

    def test_three_header_rows_round_trip(self):
        columns = [
            {"name": "wave", "unit": "nm", "dtype": "float64",
             "values": ["350.0", "950.0"]},
            {"name": "response", "unit": "ct", "dtype": "float32",
             "values": ["1.0", "2.0"]},
        ]
        headers = ("name", "unit", "dtype")
        text = write_rst_table(columns, header_rows=headers)
        self.assertEqual(read_rst_table(text, header_rows=headers), columns)
        self.assertEqual(write_rst_table(read_rst_table(text, header_rows=headers),
                                         header_rows=headers), text)

    def test_metadata_contributes_to_width(self):
        columns = [
            {"name": "x", "unit": "kilometres", "values": ["1"]},
            {"name": "long_name", "unit": "m", "values": ["2"]},
        ]
        text = write_rst_table(columns, header_rows=("name", "unit"))
        self.assertEqual(text.splitlines()[0], "========== =========")
        self.assertEqual(read_rst_table(text, header_rows=("name", "unit")), columns)

    def test_missing_values_are_rejected(self):
        with self.assertRaises(ValueError):
            write_rst_table([{"name": "left"}, {"name": "right"}])

    def test_extra_separator_in_data_is_rejected(self):
        text = "=== ===\na   b\n=== ===\n1   2\n=== ===\n3   4\n=== ===\n"
        with self.assertRaises(ValueError):
            read_rst_table(text)


if __name__ == "__main__":
    unittest.main()
